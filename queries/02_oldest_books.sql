SELECT DISTINCT h.name AS "Зал", b.title AS "Название", b.author AS "Автор",
    b.publication_year AS "Год издания", :current_year-b.publication_year AS "Возраст, лет"
FROM halls h JOIN copies c ON c.hall_id=h.id JOIN books b ON b.id=c.book_id
WHERE b.publication_year=(
    SELECT min(b2.publication_year) FROM copies c2 JOIN books b2 ON b2.id=c2.book_id
    WHERE c2.hall_id=h.id
)
ORDER BY h.name, b.title, b.author;
