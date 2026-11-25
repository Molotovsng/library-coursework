import sqlite3
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / 'data' / 'library.db'
TABLES = {'hall_types', 'knowledge_types', 'knowledge_areas', 'halls',
          'books', 'copies', 'readers', 'librarians', 'loans', 'visits'}
REPORTS = ['01_monthly_loans.sql', '02_oldest_books.sql',
           '03_halls_by_types.sql', '04_top_books.sql']


def connect(path=DEFAULT_DB):
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    return conn


def initialize(path=DEFAULT_DB, demo=True):
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        if demo:
            from init_db import seed
            with conn:
                seed(conn)
    except Exception:
        conn.close()
        path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    return True


def _table(table):
    if table not in TABLES:
        raise ValueError('Неизвестная таблица')
    return table


def save_record(conn, table, values, record_id=None):
    table = _table(table)
    allowed = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
    if not values or not set(values) <= (allowed - {'id'}):
        raise ValueError('Неверный набор полей')
    columns = list(values)
    with conn:
        if record_id is None:
            fields = ','.join(columns)
            marks = ','.join('?' for _ in columns)
            cur = conn.execute(f'INSERT INTO {table} ({fields}) VALUES ({marks})',
                               tuple(values[c] for c in columns))
            return cur.lastrowid
        fields = ','.join(f'{c}=?' for c in columns)
        conn.execute(f'UPDATE {table} SET {fields} WHERE id=?',
                     (*[values[c] for c in columns], record_id))
        return record_id


def delete_record(conn, table, record_id):
    with conn:
        conn.execute(f'DELETE FROM {_table(table)} WHERE id=?', (record_id,))


def date_iso(value):
    parsed = datetime.strptime(value, '%d/%m/%Y').date()
    if parsed.strftime('%d/%m/%Y') != value:
        raise ValueError('Введите дату строго ДД/ММ/ГГГГ')
    return parsed.isoformat()


def report(conn, number, year=None, as_of=None, type_ids=(1, 2, 3)):
    if number not in range(1, 5):
        raise ValueError('Номер отчета должен быть от 1 до 4')
    today = date.today()
    year = today.year if year is None else int(year)
    if not 1 <= year <= 9999:
        raise ValueError('Год должен быть от 1 до 9999')
    as_of = as_of or today.strftime('%d/%m/%Y')
    current = date_iso(as_of)
    chosen = sorted(set(int(t) for t in type_ids))
    if not set(chosen) <= {1, 2, 3}:
        raise ValueError('Неизвестный тип знаний')
    if number == 3 and not chosen:
        raise ValueError('Выберите хотя бы один тип знаний')
    chosen += [0] * (3 - len(chosen))
    params = {'year': year, 'current_year': int(current[:4]),
              'as_of': current, 'type1': chosen[0],
              'type2': chosen[1], 'type3': chosen[2]}
    sql = (ROOT / 'queries' / REPORTS[number - 1]).read_text(encoding='utf-8')
    cursor = conn.execute(sql, params)
    return [col[0] for col in cursor.description], [tuple(r) for r in cursor]


def error_message(exc):
    text = str(exc)
    if 'FOREIGN KEY' in text:
        return 'Запись связана с другими данными или выбран отсутствующий объект.'
    if 'UNIQUE constraint failed: loans.copy_id' in text:
        return 'Этот экземпляр уже выдан и пока не возвращен.'
    if 'UNIQUE constraint failed' in text:
        return 'Такая запись уже существует. Проверьте уникальные реквизиты.'
    if 'CHECK constraint failed' in text:
        return ('Данные нарушают правила: даты ДД/ММ/ГГГГ, возврат не раньше '
                'выдачи, телефон +7 (111) 1765880, числа положительные. '
                'Все обязательные поля должны быть заполнены.')
    if 'NOT NULL constraint' in text:
        return 'Заполните все обязательные поля.'
    return text
