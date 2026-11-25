PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE hall_types (
    id INTEGER PRIMARY KEY CHECK (id IN (1,2,3)),
    name TEXT NOT NULL UNIQUE,
    CHECK ((id=1 AND name='Зал художественной литературы')
        OR (id=2 AND name='Зал технической литературы')
        OR (id=3 AND name='Зал иностранной литературы'))
);
INSERT INTO hall_types VALUES (1,'Зал художественной литературы'),
    (2,'Зал технической литературы'),(3,'Зал иностранной литературы');
CREATE TRIGGER hall_types_no_delete BEFORE DELETE ON hall_types
BEGIN SELECT RAISE(ABORT,'Три типа залов являются обязательными'); END;

CREATE TABLE knowledge_types (
    id INTEGER PRIMARY KEY CHECK (id IN (1,2,3)),
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name))>0)
);
INSERT INTO knowledge_types VALUES (1,'Гуманитарные знания'),(2,'Технические знания'),(3,'Языки и культура');
CREATE TRIGGER knowledge_types_no_delete BEFORE DELETE ON knowledge_types
BEGIN SELECT RAISE(ABORT,'В справочнике должно оставаться ровно три типа знаний'); END;
CREATE TRIGGER knowledge_types_no_id_update BEFORE UPDATE OF id ON knowledge_types
WHEN NEW.id != OLD.id
BEGIN SELECT RAISE(ABORT,'Коды трех типов знаний неизменяемы'); END;

CREATE TABLE knowledge_areas (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name))>0),
    knowledge_type_id INTEGER NOT NULL REFERENCES knowledge_types(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE halls (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name))>0),
    hall_type_id INTEGER NOT NULL REFERENCES hall_types(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title))>0),
    author TEXT NOT NULL CHECK (length(trim(author))>0),
    publication_place TEXT NOT NULL CHECK (length(trim(publication_place))>0),
    publisher TEXT NOT NULL CHECK (length(trim(publisher))>0),
    publication_year INTEGER NOT NULL CHECK (typeof(publication_year)='integer' AND publication_year BETWEEN 1 AND 9999),
    page_count INTEGER NOT NULL CHECK (typeof(page_count)='integer' AND page_count>0),
    knowledge_area_id INTEGER NOT NULL REFERENCES knowledge_areas(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    UNIQUE (title, author, publication_year)
);
CREATE TABLE copies (
    id INTEGER PRIMARY KEY,
    inventory_number TEXT NOT NULL UNIQUE CHECK (length(trim(inventory_number))>0),
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    hall_id INTEGER NOT NULL REFERENCES halls(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE readers (
    id INTEGER PRIMARY KEY,
    ticket_number TEXT NOT NULL UNIQUE CHECK (length(trim(ticket_number))>0),
    full_name TEXT NOT NULL CHECK (length(trim(full_name))>0),
    birth_date TEXT NOT NULL CHECK (typeof(birth_date) = 'text'
        AND birth_date GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
        AND length(birth_date) = 10
        AND CAST(substr(birth_date,7,4) AS INTEGER) BETWEEN 1 AND 9999
        AND CAST(substr(birth_date,4,2) AS INTEGER) BETWEEN 1 AND 12
        AND CAST(substr(birth_date,1,2) AS INTEGER) BETWEEN 1 AND CASE
            WHEN CAST(substr(birth_date,4,2) AS INTEGER) IN (1,3,5,7,8,10,12) THEN 31
            WHEN CAST(substr(birth_date,4,2) AS INTEGER) IN (4,6,9,11) THEN 30
            WHEN CAST(substr(birth_date,7,4) AS INTEGER) % 400 = 0 OR (CAST(substr(birth_date,7,4) AS INTEGER) % 4 = 0 AND CAST(substr(birth_date,7,4) AS INTEGER) % 100 != 0) THEN 29
            ELSE 28 END),
    phone TEXT NOT NULL CHECK (length(phone)=16 AND phone GLOB '+7 ([0-9][0-9][0-9]) [0-9][0-9][0-9][0-9][0-9][0-9][0-9]')
);
CREATE TABLE librarians (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name))>0),
    phone TEXT NOT NULL CHECK (length(phone)=16 AND phone GLOB '+7 ([0-9][0-9][0-9]) [0-9][0-9][0-9][0-9][0-9][0-9][0-9]')
);
CREATE TABLE loans (
    id INTEGER PRIMARY KEY,
    copy_id INTEGER NOT NULL REFERENCES copies(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    reader_id INTEGER NOT NULL REFERENCES readers(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    librarian_id INTEGER NOT NULL REFERENCES librarians(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    issue_date TEXT NOT NULL CHECK (typeof(issue_date) = 'text'
        AND issue_date GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
        AND length(issue_date) = 10
        AND CAST(substr(issue_date,7,4) AS INTEGER) BETWEEN 1 AND 9999
        AND CAST(substr(issue_date,4,2) AS INTEGER) BETWEEN 1 AND 12
        AND CAST(substr(issue_date,1,2) AS INTEGER) BETWEEN 1 AND CASE
            WHEN CAST(substr(issue_date,4,2) AS INTEGER) IN (1,3,5,7,8,10,12) THEN 31
            WHEN CAST(substr(issue_date,4,2) AS INTEGER) IN (4,6,9,11) THEN 30
            WHEN CAST(substr(issue_date,7,4) AS INTEGER) % 400 = 0 OR (CAST(substr(issue_date,7,4) AS INTEGER) % 4 = 0 AND CAST(substr(issue_date,7,4) AS INTEGER) % 100 != 0) THEN 29
            ELSE 28 END),
    return_date TEXT CHECK (return_date IS NULL OR (typeof(return_date) = 'text'
        AND return_date GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
        AND length(return_date) = 10
        AND CAST(substr(return_date,7,4) AS INTEGER) BETWEEN 1 AND 9999
        AND CAST(substr(return_date,4,2) AS INTEGER) BETWEEN 1 AND 12
        AND CAST(substr(return_date,1,2) AS INTEGER) BETWEEN 1 AND CASE
            WHEN CAST(substr(return_date,4,2) AS INTEGER) IN (1,3,5,7,8,10,12) THEN 31
            WHEN CAST(substr(return_date,4,2) AS INTEGER) IN (4,6,9,11) THEN 30
            WHEN CAST(substr(return_date,7,4) AS INTEGER) % 400 = 0 OR (CAST(substr(return_date,7,4) AS INTEGER) % 4 = 0 AND CAST(substr(return_date,7,4) AS INTEGER) % 100 != 0) THEN 29
            ELSE 28 END)),
    CHECK (return_date IS NULL OR (substr(return_date,7,4)||'-'||substr(return_date,4,2)||'-'||substr(return_date,1,2)) >= (substr(issue_date,7,4)||'-'||substr(issue_date,4,2)||'-'||substr(issue_date,1,2)))
);
CREATE UNIQUE INDEX ux_loans_active_copy ON loans(copy_id) WHERE return_date IS NULL;
CREATE INDEX ix_loans_reader ON loans(reader_id);
CREATE INDEX ix_loans_issue_date ON loans((substr(issue_date,7,4)||'-'||substr(issue_date,4,2)||'-'||substr(issue_date,1,2)));
CREATE INDEX ix_copies_book ON copies(book_id);
CREATE INDEX ix_copies_hall ON copies(hall_id);
CREATE INDEX ix_books_area ON books(knowledge_area_id);

CREATE TRIGGER loans_validate_insert BEFORE INSERT ON loans WHEN NEW.return_date IS NULL
BEGIN
    SELECT CASE WHEN (SELECT count(*) FROM loans WHERE reader_id=NEW.reader_id AND return_date IS NULL)>=5
        THEN RAISE(ABORT,'Читателю уже выдано 5 книг') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM loans l JOIN copies c ON c.id=l.copy_id
        WHERE l.reader_id=NEW.reader_id AND l.return_date IS NULL
        AND c.book_id=(SELECT book_id FROM copies WHERE id=NEW.copy_id))
        THEN RAISE(ABORT,'У читателя уже есть экземпляр этого издания') END;
END;
CREATE TRIGGER loans_validate_update BEFORE UPDATE ON loans WHEN NEW.return_date IS NULL
BEGIN
    SELECT CASE WHEN (SELECT count(*) FROM loans WHERE reader_id=NEW.reader_id AND return_date IS NULL AND id!=OLD.id)>=5
        THEN RAISE(ABORT,'Читателю уже выдано 5 книг') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM loans l JOIN copies c ON c.id=l.copy_id
        WHERE l.reader_id=NEW.reader_id AND l.return_date IS NULL AND l.id!=OLD.id
        AND c.book_id=(SELECT book_id FROM copies WHERE id=NEW.copy_id))
        THEN RAISE(ABORT,'У читателя уже есть экземпляр этого издания') END;
END;
CREATE TRIGGER copies_preserve_book BEFORE UPDATE OF book_id ON copies
WHEN NEW.book_id!=OLD.book_id AND EXISTS (SELECT 1 FROM loans WHERE copy_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'Нельзя менять издание экземпляра с историей выдач'); END;

CREATE TABLE visits (
    id INTEGER PRIMARY KEY,
    reader_id INTEGER NOT NULL REFERENCES readers(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    hall_id INTEGER NOT NULL REFERENCES halls(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    visit_date TEXT NOT NULL CHECK (typeof(visit_date) = 'text'
        AND visit_date GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
        AND length(visit_date) = 10
        AND CAST(substr(visit_date,7,4) AS INTEGER) BETWEEN 1 AND 9999
        AND CAST(substr(visit_date,4,2) AS INTEGER) BETWEEN 1 AND 12
        AND CAST(substr(visit_date,1,2) AS INTEGER) BETWEEN 1 AND CASE
            WHEN CAST(substr(visit_date,4,2) AS INTEGER) IN (1,3,5,7,8,10,12) THEN 31
            WHEN CAST(substr(visit_date,4,2) AS INTEGER) IN (4,6,9,11) THEN 30
            WHEN CAST(substr(visit_date,7,4) AS INTEGER) % 400 = 0 OR (CAST(substr(visit_date,7,4) AS INTEGER) % 4 = 0 AND CAST(substr(visit_date,7,4) AS INTEGER) % 100 != 0) THEN 29
            ELSE 28 END)
);
CREATE INDEX ix_visits_reader_date ON visits(reader_id, visit_date);
COMMIT;
