WITH RECURSIVE months(month_no) AS (
    SELECT 1 UNION ALL SELECT month_no+1 FROM months WHERE month_no<12
)
SELECT m.month_no AS "Месяц", count(l.id) AS "Количество выдач"
FROM months m LEFT JOIN loans l
    ON CAST(substr(l.issue_date,4,2) AS INTEGER)=m.month_no
    AND CAST(substr(l.issue_date,7,4) AS INTEGER)=:year
GROUP BY m.month_no ORDER BY m.month_no;
