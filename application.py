import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import plotly
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import json

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///weekyou.db")

#### roles -------------------------------

@app.route("/roles", methods=["GET", "POST"])
@login_required
def roles():
    if request.method == "GET":
        roles = db.execute("SELECT * FROM roles WHERE userId = :userId and isDeleted = 0", userId = session["user_id"])
        return render_template("roles.html", roles = roles)
    if request.method == "POST":
        # get data from submition
        roleName = request.form.get("roleName")
        longTerm = request.form.get("longTerm")
        # check if role already exists
        role_name_check = db.execute("SELECT * FROM roles WHERE userId = :userId and isDeleted = 0 AND name = :roleName", userId = session["user_id"], roleName = roleName)
        if len(role_name_check):
            return apology("Role already exists")
        db.execute("INSERT INTO roles (userId, name, description, createdAt, weekStart) VALUES (:userId, :name, :description, :createdAt, DATE('now','localtime','weekday 0','-6 days'))",
                    userId = session["user_id"],
                    name = roleName,
                    description = longTerm,
                    createdAt = datetime.now())
        return redirect("/roles")

@app.route("/roles/delete/<int:roleId>")
@login_required
def delete_role(roleId):
    db.execute("UPDATE roles SET isDeleted = 1, deletedAtWeekStart = DATE('now','localtime','weekday 0','-6 days') WHERE id = :roleId",
                roleId = roleId)
    db.execute("UPDATE tasks SET status = 4 WHERE roleId = :roleId AND weekStart = DATE('now','localtime','weekday 0','-6 days')",
                roleId = roleId)
    return redirect("/roles")

@app.route("/roles/edit/<int:roleId>", methods=["GET", "POST"])
@login_required
def edit_role(roleId):
    if request.method == "GET":
        roles = db.execute("SELECT * FROM roles WHERE userId = :userId and isDeleted = 0", userId = session["user_id"])
        return render_template("edit-roles.html", edit_role_id = roleId, roles = roles)
    if request.method == "POST":
        # get data from submition
        roleName_edit = request.form.get("edit-roleName")
        longTerm_edit = request.form.get("edit-longTerm")
        db.execute("UPDATE roles SET name = :roleName_edit, description = :longTerm_edit WHERE id = :roleId",
                    roleId = roleId,
                    roleName_edit = roleName_edit,
                    longTerm_edit = longTerm_edit)
        return redirect("/roles")

###############################

### tasks

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    tasks = db.execute("SELECT t.id, t.name as taskName, R.name as roleName, t.status  \
                        FROM tasks AS t LEFT JOIN roles AS R ON t.roleId = R.id WHERE R.userId = :userId and t.weekStart = DATE('now','localtime','weekday 0','-6 days') AND t.status != 4 AND R.isDeleted = 0",
                        userId = session["user_id"])
    tasks_stats = db.execute("SELECT SUM(inProgress) as inProgress, SUM(completed) AS completed FROM( \
                            SELECT *, \
                            CASE WHEN t.status = 1 THEN 1 \
                            ELSE 0 END AS inProgress, \
                            CASE WHEN t.status = 2 THEN 1 \
                            ELSE 0 END AS completed \
                            FROM tasks AS T \
                            LEFT JOIN roles as R ON R.id = T.roleId WHERE R.isDeleted = 0 AND T.userId = :userId AND t.status IN (1,2) AND t.weekStart = DATE('now','localtime','weekday 0','-6 days'))A", userId=session["user_id"])
    if request.method == "GET":
        roles = db.execute("SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R LEFT JOIN (SELECT * FROM TASKS WHERE status = 1) AS T ON R.id = t.roleId WHERE R.userId = :userId AND R.isDeleted = 0 GROUP BY R.Name", userId = session["user_id"])
        return render_template("homepage.html", roles = roles, tasks = tasks, tasks_stats = tasks_stats)

    else:
        roleName = request.form.get("roleName")
        shortTerm = request.form.get("shortTerm")
        # need to get role id
        roleId = db.execute("SELECT id FROM roles WHERE userId = :userId AND name = :roleName AND isDeleted = 0",
                    userId = session["user_id"],
                    roleName = roleName)[0]["id"]
        # update tasks
        db.execute("INSERT INTO tasks (roleId, name, weekStart, createdAt, dueAt, userId) VALUES (:roleId, :name, DATE('now','localtime','weekday 0','-6 days'), :createdAt, DATE('now', 'weekday 0', '+1 days'), :userId)",
            userId = session["user_id"],
            roleId = roleId,
            name = shortTerm,
            createdAt = datetime.now())
        tasks = db.execute("SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t LEFT JOIN roles AS R ON t.roleId = R.id \
                            WHERE R.userId = :userId and t.weekStart = DATE('now','localtime','weekday 0','-6 days') AND t.status != 4 AND R.isDeleted = 0",
                        userId = session["user_id"])
        roles = db.execute("SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R LEFT JOIN (SELECT * FROM TASKS WHERE status = 1) AS T ON R.id = t.roleId WHERE R.userId = :userId AND R.isDeleted = 0 GROUP BY R.Name", userId = session["user_id"])
        tasks_stats = db.execute("SELECT SUM(inProgress) as inProgress, SUM(completed) AS completed FROM( \
                                SELECT *, \
                                CASE WHEN t.status = 1 THEN 1 \
                                ELSE 0 END AS inProgress, \
                                CASE WHEN t.status = 2 THEN 1 \
                                ELSE 0 END AS completed \
                                FROM tasks AS T \
                                LEFT JOIN roles as R ON R.id = T.roleId WHERE R.isDeleted = 0 AND T.userId = :userId AND t.status IN (1,2) AND t.weekStart = DATE('now','localtime','weekday 0','-6 days'))A", userId=session["user_id"])
        return render_template("homepage.html", roles = roles, tasks = tasks, tasks_stats = tasks_stats)

@app.route("/tasks/delete/<int:taskId>")
@login_required
def delete_task(taskId):
    db.execute("UPDATE tasks SET status = 4 WHERE id = :taskId AND userId = :userId",
        taskId = taskId,
        userId = session["user_id"])
    return redirect("/")

@app.route("/tasks/complete/<int:taskId>")
@login_required
def complete_task(taskId):
    db.execute("UPDATE tasks SET status = 2 WHERE id = :taskId AND userId = :userId",
        taskId = taskId,
        userId = session["user_id"])
    return redirect("/")

@app.route("/tasks/uncomplete/<int:taskId>")
@login_required
def uncomplete_task(taskId):
    db.execute("UPDATE tasks SET status = 1 WHERE id = :taskId AND userId = :userId",
        taskId = taskId,
        userId = session["user_id"])
    return redirect("/")

@app.route("/tasks/edit/<int:taskId>", methods=["GET", "POST"])
@login_required
def edit_task(taskId):
    roles = db.execute("SELECT * FROM roles WHERE userId = :userId and isDeleted = 0", userId = session["user_id"])
    tasks = db.execute("SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t LEFT JOIN roles AS R ON t.roleId = R.id WHERE R.userId = :userId and t.weekStart = DATE('now','localtime','weekday 0','-6 days') AND t.status != 4",
                        userId = session["user_id"])
    if request.method == "GET":
        return render_template("homepage-edit.html", roles = roles, tasks = tasks, edit_task_id = taskId)

#########################################

####### reflect

@app.route("/reflect", methods=["GET", "POST"])
@login_required
def reflect():
    dates = db.execute("SELECT DISTINCT t.weekStart AS date FROM tasks AS t LEFT JOIN roles AS R ON t.roleId = R.id \
                        WHERE R.userId = :userId AND t.status != 4 ORDER BY t.weekStart DESC", userId = session["user_id"])
    if request.method == "GET" and len(dates) > 0:
        tasks = db.execute("SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t \
                            LEFT JOIN roles AS R ON t.roleId = R.id \
                            WHERE R.userId = :userId and t.weekStart = :weekStart AND t.status != 4 AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL)",
                            userId = session["user_id"], weekStart = dates[0]['date'])
        roles = db.execute("SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 2 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name", userId = session["user_id"], weekStart = dates[0]['date'])
        done = db.execute("SELECT SUM (number_1) AS done FROM (SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 2 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name)A", userId = session["user_id"], weekStart = dates[0]['date'])

        unsuccessful = db.execute("SELECT SUM (number_1) AS unsuccessful FROM (SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 3 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name)A", userId = session["user_id"], weekStart = dates[0]['date'])
        all_tasks = db.execute("SELECT COUNT(id) AS all_tasks FROM (SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t \
                    LEFT JOIN roles AS R ON t.roleId = R.id \
                    WHERE R.userId = :userId and t.weekStart = :weekStart AND t.status != 4 AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL))A",
                    userId = session["user_id"], weekStart = dates[0]['date'])
        now = datetime.now()
        monday = now - timedelta(days = now.weekday())
        return render_template("reflect.html", roles = roles, tasks = tasks, dates = dates,
                                done = done[0]["done"], unsuccessful = unsuccessful[0]["unsuccessful"], percent = int(int(done[0]["done"])/int(all_tasks[0]["all_tasks"])*100),
                                selected_date = dates[0]["date"])

    if request.method == "GET" and len(dates) == 0:
        return render_template("reflect-sorry.html")

    if request.method == "POST":
        form_date = request.form.get("dateform")
        tasks = db.execute("SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t \
                            LEFT JOIN roles AS R ON t.roleId = R.id \
                            WHERE R.userId = :userId and t.weekStart = :weekStart AND t.status != 4 AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL)",
                            userId = session["user_id"],
                            weekStart = form_date)
        roles = db.execute("SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 2 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name", userId = session["user_id"], weekStart = form_date)
        done = db.execute("SELECT SUM (number_1) AS done FROM (SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 2 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name)A", userId = session["user_id"], weekStart = form_date)

        unsuccessful = db.execute("SELECT SUM (number_1) AS unsuccessful FROM (SELECT R.name, COUNT(T.Id) AS number_1 FROM ROLES AS R \
                            LEFT JOIN (SELECT * FROM TASKS  \
                            WHERE status = 3 AND weekStart = :weekStart) AS T ON R.id = t.roleId \
                            WHERE R.userId = :userId AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL) AND R.weekStart <= :weekStart \
                            GROUP BY R.Name)A", userId = session["user_id"], weekStart = form_date)
        all_tasks = db.execute("SELECT COUNT(id) AS all_tasks FROM (SELECT t.id, t.name as taskName, R.name as roleName, t.status FROM tasks AS t \
                    LEFT JOIN roles AS R ON t.roleId = R.id \
                    WHERE R.userId = :userId and t.weekStart = :weekStart AND t.status != 4 AND (R.deletedAtWeekStart > :weekStart OR R.deletedAtWeekStart IS NULL))A",
                    userId = session["user_id"], weekStart = form_date)
        return render_template("reflect.html", roles = roles, tasks = tasks, dates = dates,
                                done = done[0]["done"], unsuccessful = unsuccessful[0]["unsuccessful"], percent = int(int(done[0]["done"])/int(all_tasks[0]["all_tasks"])*100),
                                selected_date = form_date)

#########################################


################# track

@app.route('/track')
@login_required
def track():

    data = db.execute("SELECT weekStart, status, count(*) AS skaicius \
                      FROM tasks \
                      WHERE userId = :userId AND status != 4 \
                      GROUP BY weekStart, status", userId = session["user_id"])

    if len(data) > 0:

        df = pd.DataFrame(data)

        def create_plot():

            data=[
                go.Bar(name='Pending', x=pd.unique(df.query("status == 1")['weekStart']), y=df.query("status == 1")['skaicius']),
                go.Bar(name='Success', x=pd.unique(df.query("status == 2")['weekStart']), y=df.query("status == 2")['skaicius']),
                go.Bar(name='Unsuccessful', x=pd.unique(df.query("status == 3")['weekStart']), y=df.query("status == 3")['skaicius'])
            ]

            graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

            return graphJSON

        all_tasks = sum(df.skaicius)
        all_success = sum(df.query("status == 2")['skaicius'])

        bar = create_plot()
        return render_template('track.html', plot=bar, all_tasks = all_tasks, all_success = all_success)

    else:
        return render_template("reflect-sorry.html")

###########

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for email
        rows = db.execute("SELECT * FROM users WHERE email = :email",
                          email=request.form.get("email"))

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # fix overdue taxt to status = 3 - unsuccessful

        db.execute("UPDATE tasks SET status = 3 WHERE userId = :user_id AND dueAt <= :today_date AND status NOT IN (2, 4)",
        user_id = session["user_id"],
        today_date = datetime.now())

        # check if first log in

        first_login = db.execute("SELECT introDone FROM users WHERE id = :id",
                              id = session["user_id"])
        if first_login[0]["introDone"] == 0:
            return redirect("/intro")

        # Redirect user to home page
        return redirect("/")


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

### intro

@app.route("/intro")
@login_required
def intro():
    return render_template("intro.html")

@app.route("/intro/done")
@login_required
def intro_dne():
    db.execute("UPDATE users SET introDone = :introDone WHERE id = :user_id",
    user_id = session["user_id"],
    introDone = 1)
    return redirect("/roles")

### register

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # check if email was provided
        if not email:
            return apology("You must provide a email")
        # check if passowrd or confirmation was provided
        if not password or not confirmation:
            return apology("You must provide a password")
        #check if email already exists in the db
        rows = db.execute("SELECT * FROM users WHERE email = :email",
                          email=email)
        if len(rows) != 0:
            return apology("email already taken")
        #check if passwords match
        if password != confirmation:
            return apology("Passwords do not match")
        #hash password
        hash = generate_password_hash(password)
        #register an account into a db
        db.execute("INSERT INTO users (email, hash, createdAt) VALUES (:email, :hash, :createdAt)",
                    email = email,
                    hash = hash,
                    createdAt = datetime.now())
        return redirect("/")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
