SELECT weekStart, status, count(*)
FROM tasks
WHERE userId = 8 AND status != 4
GROUP BY weekStart, status