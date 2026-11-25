SELECT b.title AS "Название", b.author AS "Автор", b.publication_year AS "Год издания",
    count(l.id) AS "Количество выдач"
FROM loans l JOIN copies c ON c.id=l.copy_id JOIN books b ON b.id=c.book_id
WHERE (substr(l.issue_date,7,4)||'-'||substr(l.issue_date,4,2)||'-'||substr(l.issue_date,1,2))
    >=date(:as_of,'start of month','-1 month')
AND (substr(l.issue_date,7,4)||'-'||substr(l.issue_date,4,2)||'-'||substr(l.issue_date,1,2))
    <date(:as_of,'start of month')
GROUP BY b.id,b.title,b.author,b.publication_year
ORDER BY count(l.id) DESC,b.title,b.author,b.publication_year,b.id LIMIT 5;
