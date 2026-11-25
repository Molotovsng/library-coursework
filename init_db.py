import argparse
from pathlib import Path
from db import DEFAULT_DB, initialize


def seed(conn):
    conn.executemany('INSERT INTO knowledge_areas VALUES (?,?,?)', [
        (1, 'Художественная проза', 1), (2, 'История', 1),
        (3, 'Программирование', 2), (4, 'Инженерное дело', 2),
        (5, 'Иностранные языки', 3), (6, 'Культура стран мира', 3)])
    conn.executemany('INSERT INTO halls VALUES (?,?,?)', [
        (1, 'Художественный зал № 1', 1), (2, 'Технический зал № 1', 2),
        (3, 'Иностранный зал № 1', 3), (4, 'Универсальный зал № 2', 1),
        (5, 'Новый зал без фонда', 2)])
    books = [
        ('Северные огни', 'Леснов А. П.', 1960, 240, 1),
        ('Тихая пристань', 'Речной И. С.', 1960, 180, 1),
        ('История бумажного города', 'Сказов Е. М.', 1988, 320, 2),
        ('Практика алгоритмов', 'Кодов Д. А.', 2019, 384, 3),
        ('Мастерская баз данных', 'Табличная Н. В.', 2023, 256, 3),
        ('Механика простых устройств', 'Винтов П. К.', 1975, 208, 4),
        ('Путешествие в английский', 'Словина М. Л.', 2016, 224, 5),
        ('Культурные маршруты', 'Мирова Е. Н.', 1975, 304, 6),
        ('Разговорный французский', 'Языков С. О.', 2021, 168, 5),
        ('Сети для начинающих', 'Пакетов Р. И.', 2020, 288, 3)]
    for n, (title, author, year, pages, area) in enumerate(books, 1):
        conn.execute('INSERT INTO books VALUES (?,?,?,?,?,?,?,?)',
                     (n, title, author, 'Учебный город', 'Демо-издательство',
                      year, pages, area))
    hall_for_book = [1, 1, 1, 2, 2, 2, 3, 3, 3, 2]
    for book, hall in enumerate(hall_for_book, 1):
        for offset in (0, 1):
            copy = (book - 1) * 2 + offset + 1
            conn.execute('INSERT INTO copies VALUES (?,?,?,?)',
                         (copy, f'ИНВ-{copy:04}', book, hall))
    for copy, book in [(21, 1), (22, 4), (23, 7)]:
        conn.execute('INSERT INTO copies VALUES (?,?,?,4)',
                     (copy, f'ИНВ-{copy:04}', book))
    names = ['Иванов Алексей Сергеевич', 'Петрова Мария Игоревна',
             'Сидоров Павел Олегович', 'Смирнова Анна Андреевна',
             'Кузнецов Дмитрий Львович', 'Волкова Елена Петровна',
             'Соколова Ирина Николаевна', 'Морозов Сергей Васильевич']
    for n, name in enumerate(names, 1):
        conn.execute('INSERT INTO readers VALUES (?,?,?,?,?)',
                     (n, f'Ч-{n:04}', name, f'{n:02}/05/{1988+n}',
                      f'+7 (900) {1000000+n}'))
    conn.executemany('INSERT INTO librarians VALUES (?,?,?)', [
        (1, 'Книжная Ольга Ивановна', '+7 (901) 1000001'),
        (2, 'Читальников Антон Петрович', '+7 (901) 1000002')])
    for book, demand in enumerate((6, 5, 4, 3, 2, 1, 1), 1):
        for j in range(demand):
            day = 1 + j * 3
            conn.execute('''INSERT INTO loans
                (copy_id,reader_id,librarian_id,issue_date,return_date)
                VALUES (?,?,?,?,?)''',
                ((book-1)*2+1, (j+book-1)%8+1, j%2+1,
                 f'{day:02}/09/2026', f'{day+1:02}/09/2026'))
    for month, book in [(1, 8), (3, 9), (6, 10), (8, 2)]:
        conn.execute('''INSERT INTO loans
            (copy_id,reader_id,librarian_id,issue_date,return_date)
            VALUES (?,?,1,?,?)''',
            ((book-1)*2+1, book%8+1,
             f'10/{month:02}/2026', f'12/{month:02}/2026'))
    for book in (4, 5, 6):
        conn.execute('''INSERT INTO loans
            (copy_id,reader_id,librarian_id,issue_date) VALUES (?,1,1,?)''',
            ((book-1)*2+2, '02/10/2026'))
    for n in range(1, 31):
        conn.execute('INSERT INTO visits (reader_id,hall_id,visit_date) VALUES (?,?,?)',
                     ((n-1)%8+1, (n-1)%4+1, f'{(n-1)%28+1:02}/09/2026'))
    conn.execute("INSERT INTO visits (reader_id,hall_id,visit_date) VALUES (1,2,'02/10/2026')")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Создать новую базу библиотеки')
    parser.add_argument('--path', type=Path, default=DEFAULT_DB)
    parser.add_argument('--empty', action='store_true', help='Создать без демоданных')
    args = parser.parse_args()
    created = initialize(args.path, demo=not args.empty)
    print(('Создана: ' if created else 'Файл уже существует, сохранен: ') + str(args.path))
