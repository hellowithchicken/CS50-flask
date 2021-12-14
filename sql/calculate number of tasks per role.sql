SELECT R.Name, COUNT(T.Id) FROM
ROLES AS R
LEFT JOIN TASKS AS T ON R.id = t.roleId
WHERE (T.Status = 1 OR T.Status IS NULL) AND R.userId = 1 AND R.isDeleted = 0
GROUP BY R.Name;
