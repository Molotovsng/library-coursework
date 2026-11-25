SELECT h.name AS "Зал", ht.name AS "Тип зала", count(c.id) AS "Экземпляров"
FROM halls h JOIN hall_types ht ON ht.id=h.hall_type_id JOIN copies c ON c.hall_id=h.id
WHERE NOT EXISTS (
    SELECT 1 FROM copies cx JOIN books b ON b.id=cx.book_id
    JOIN knowledge_areas a ON a.id=b.knowledge_area_id
    WHERE cx.hall_id=h.id AND a.knowledge_type_id NOT IN (:type1,:type2,:type3)
)
GROUP BY h.id,h.name,ht.name ORDER BY h.name;
