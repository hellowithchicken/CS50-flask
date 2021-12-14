CREATE TABLE 'tasks'(
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	roleId INTEGER NOT NULL,
	name TEXT NOT NULL,
	status INTEGER NOT NULL DEFAULT 1,
	weekStart DATETIME NOT NULL,
	createdAt DATETIME NOT NULL,
	dueAt DATETIME NOT NULL,
	completedAt DATETIME,
    isDeleted boolean NOT NULL DEFAULT 0,
	FOREIGN KEY(roleId) REFERENCES roles(id)
	)