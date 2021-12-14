CREATE TABLE IF NOT EXISTS 'users' (
        'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        'email' TEXT NOT NULL,
        'hash' TEXT NOT NULL,
        'introDone' boolean NOT NULL DEFAULT 0,
        'CreatedAt' DATETIME NOT NULL);
CREATE UNIQUE INDEX 'username' ON "users" ("username");