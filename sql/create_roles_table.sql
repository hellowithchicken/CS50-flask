CREATE TABLE 'roles'(
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	userId INTEGER NOT NULL,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	createdAt DATETIME NOT NULL,
    isDeleted boolean NOT NULL DEFAULT 0,
	FOREIGN KEY(userId) REFERENCES users(id)
	)