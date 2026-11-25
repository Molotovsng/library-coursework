import argparse
import csv
import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, simpledialog
import db

FIELDS = {
    'books': ('Каталог изданий', [
        ('title', 'Название', 'text'), ('author', 'Автор', 'text'),
        ('publication_place', 'Место издания', 'text'),
        ('publisher', 'Издательство', 'text'),
        ('publication_year', 'Год издания', 'int'),
        ('page_count', 'Страниц', 'int'),
        ('knowledge_area_id', 'Область знаний', 'ref:knowledge_areas')]),
    'copies': ('Экземпляры', [
        ('inventory_number', 'Инвентарный номер', 'text'),
        ('book_id', 'Издание', 'ref:books'), ('hall_id', 'Зал', 'ref:halls')]),
    'readers': ('Читатели', [
        ('ticket_number', 'Номер билета', 'text'),
        ('full_name', 'ФИО', 'text'), ('birth_date', 'Дата рождения', 'date'),
        ('phone', 'Телефон', 'text')]),
    'librarians': ('Библиотекари', [
        ('full_name', 'ФИО', 'text'), ('phone', 'Телефон', 'text')]),
    'loans': ('Выдачи и возвраты', [
        ('copy_id', 'Экземпляр', 'ref:copies'),
        ('reader_id', 'Читатель', 'ref:readers'),
        ('librarian_id', 'Библиотекарь', 'ref:librarians'),
        ('issue_date', 'Дата выдачи', 'date'),
        ('return_date', 'Дата возврата (необязательно)', 'date?')]),
    'visits': ('Посещения', [
        ('reader_id', 'Читатель', 'ref:readers'),
        ('hall_id', 'Зал', 'ref:halls'), ('visit_date', 'Дата посещения', 'date')]),
    'halls': ('Читальные залы', [
        ('name', 'Название', 'text'), ('hall_type_id', 'Тип зала', 'ref:hall_types')]),
    'knowledge_areas': ('Области знаний', [
        ('name', 'Название', 'text'),
        ('knowledge_type_id', 'Тип знаний', 'ref:knowledge_types')]),
    'knowledge_types': ('Типы знаний', [('name', 'Название', 'text')]),
    'hall_types': ('Типы залов', [('name', 'Название', 'text')])}
REPORT_NAMES = ['1. Выдачи по месяцам', '2. Старейшие книги по залам',
                '3. Залы по типам знаний', '4. Топ-5 за прошлый месяц']


def choices(conn, table):
    rows = conn.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
    result = {}
    for row in rows:
        if table == 'books':
            label = f"{row['title']} — {row['author']}, {row['publication_year']}"
        elif table == 'copies':
            book = conn.execute('SELECT title FROM books WHERE id=?',
                                (row['book_id'],)).fetchone()[0]
            label = f"{row['inventory_number']} — {book}"
        elif table == 'readers':
            label = f"{row['ticket_number']} — {row['full_name']}"
        else:
            label = row['full_name'] if 'full_name' in row.keys() else row['name']
        result[row['id']] = f"{row['id']} · {label}"
    return result


class RecordForm(tk.Toplevel):
    def __init__(self, app, table, record=None):
        super().__init__(app)
        self.app, self.table, self.record = app, table, record
        self.title(('Изменить: ' if record else 'Добавить: ') + FIELDS[table][0])
        self.transient(app)
        self.resizable(True, False)
        self.columnconfigure(1, weight=1)
        self.entries = {}
        for n, (field, label, kind) in enumerate(FIELDS[table][1]):
            ttk.Label(self, text=label).grid(row=n, column=0, sticky='w',
                                           padx=14, pady=7)
            var = tk.StringVar()
            mapping = {}
            if kind.startswith('ref:'):
                mapping = choices(app.conn, kind[4:])
                widget = ttk.Combobox(self, textvariable=var, state='readonly',
                                      values=list(mapping.values()), width=62)
                if record:
                    var.set(mapping.get(record[field], ''))
            else:
                widget = ttk.Entry(self, textvariable=var, width=65)
                if record:
                    var.set('' if record[field] is None else str(record[field]))
                elif kind == 'date' and field != 'birth_date':
                    var.set(date.today().strftime('%d/%m/%Y'))
            widget.grid(row=n, column=1, sticky='ew', padx=14, pady=7)
            self.entries[field] = (var, kind, mapping)
            if n == 0:
                widget.focus_set()
        n = len(FIELDS[table][1])
        hint = 'Даты: ДД/ММ/ГГГГ. Телефон: +7 (111) 1765880.'
        ttk.Label(self, text=hint, foreground='#536579').grid(
            row=n, column=0, columnspan=2, padx=14, pady=9, sticky='w')
        bar = ttk.Frame(self)
        bar.grid(row=n+1, column=0, columnspan=2, sticky='e', padx=14, pady=12)
        ttk.Button(bar, text='Отмена', command=self.destroy).pack(side='right')
        ttk.Button(bar, text='Сохранить', command=self.save).pack(side='right', padx=8)
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Return>', lambda event: self.save())
        self.grab_set()

    def save(self):
        try:
            values = {}
            for field, (var, kind, mapping) in self.entries.items():
                value = var.get().strip()
                if kind.startswith('ref:'):
                    reverse = {v: k for k, v in mapping.items()}
                    if value not in reverse:
                        raise ValueError('Выберите связанные записи из списков.')
                    value = reverse[value]
                elif kind == 'int':
                    value = int(value)
                elif kind.startswith('date'):
                    if kind.endswith('?') and not value:
                        value = None
                    else:
                        db.date_iso(value)
                elif not value:
                    raise ValueError('Заполните обязательные поля.')
                values[field] = value
            db.save_record(self.app.conn, self.table, values,
                           self.record['id'] if self.record else None)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('Не удалось сохранить', db.error_message(exc), parent=self)
            return
        self.app.refresh()
        self.destroy()


class LibraryApp(tk.Tk):
    def __init__(self, path=db.DEFAULT_DB):
        super().__init__()
        self.title('Библиотека')
        self.geometry('1280x760')
        self.minsize(1024, 620)
        db.initialize(path)
        self.conn = db.connect(path)
        self.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Treeview', rowheight=28, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', padding=(9, 6))
        style.configure('Title.TLabel', font=('Segoe UI', 19, 'bold'))
        side = ttk.Frame(self, padding=12)
        side.pack(side='left', fill='y')
        ttk.Label(side, text='БИБЛИОТЕКА', font=('Segoe UI', 14, 'bold')).pack(
            anchor='w', pady=(5, 15))
        for table, (label, _) in FIELDS.items():
            ttk.Button(side, text=label, width=23,
                       command=lambda t=table: self.show_table(t)).pack(fill='x', pady=3)
        ttk.Separator(side).pack(fill='x', pady=12)
        ttk.Button(side, text='Отчеты', command=self.show_reports).pack(fill='x')
        ttk.Label(side, text='Локальная база SQLite\nФормат даты: ДД/ММ/ГГГГ',
                  foreground='#536579').pack(side='bottom', anchor='w', pady=12)
        self.content = ttk.Frame(self, padding=(12, 20, 20, 12))
        self.content.pack(side='right', fill='both', expand=True)
        self.status = tk.StringVar()
        self.table = None
        self.show_table('books')

    def clear(self, title, hint):
        for widget in self.content.winfo_children():
            widget.destroy()
        ttk.Label(self.content, text=title, style='Title.TLabel').pack(anchor='w')
        ttk.Label(self.content, text=hint, foreground='#536579',
                  wraplength=950).pack(anchor='w', pady=(7, 12))

    def make_tree(self, headers):
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, pady=10)
        self.tree = ttk.Treeview(frame, columns=list(range(len(headers))),
                                 show='headings', selectmode='browse')
        vertical = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.headers = headers
        for n, label in enumerate(headers):
            width = 65 if label in ('ID', 'Страниц', 'Месяц') else 190
            if label in ('Название', 'Автор', 'Читатель', 'Экземпляр', 'Издание', 'Зал'):
                width = 245
            self.tree.heading(n, text=label)
            self.tree.column(n, width=width, minwidth=55, anchor='w')
        ttk.Label(self.content, textvariable=self.status).pack(anchor='w')

    def show_table(self, table):
        self.table = table
        hint = 'Добавляйте и редактируйте записи. Поиск применяется ко всем видимым полям.'
        if table == 'loans':
            hint = 'Не более 5 активных выдач. Один экземпляр издания на читателя. Пустой возврат = книга у читателя.'
        elif table == 'copies':
            hint = 'Каждый экземпляр имеет свой инвентарный номер и зал. Издание экземпляра с историей выдач изменять нельзя.'
        elif table == 'visits':
            hint = 'Посещения регистрируются отдельно от выдач. Несколько посещений в один день допускаются.'
        elif table == 'knowledge_types':
            hint = 'Ровно три типа знаний. Можно изменить их названия.'
        elif table == 'hall_types':
            hint = 'Три фиксированных типа читальных залов из условия задания.'
        self.clear(FIELDS[table][0], hint)
        bar = ttk.Frame(self.content)
        bar.pack(fill='x')
        if table not in ('hall_types', 'knowledge_types'):
            ttk.Button(bar, text='Добавить', command=self.add).pack(side='left', padx=(0, 6))
        if table != 'hall_types':
            ttk.Button(bar, text='Изменить', command=self.edit).pack(side='left', padx=6)
        if table not in ('hall_types', 'knowledge_types'):
            ttk.Button(bar, text='Удалить', command=self.delete).pack(side='left', padx=6)
        if table == 'loans':
            ttk.Button(bar, text='Оформить возврат', command=self.return_book).pack(side='left', padx=6)
        ttk.Button(bar, text='Экспорт CSV', command=self.export).pack(side='right')
        search = ttk.Frame(self.content)
        search.pack(fill='x', pady=(10, 0))
        ttk.Label(search, text='Поиск:').pack(side='left', padx=(0, 8))
        self.filter_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.filter_var).pack(side='left', fill='x', expand=True)
        ttk.Button(search, text='Обновить', command=self.refresh).pack(side='left', padx=(8, 0))
        self.make_tree(['ID'] + [field[1] for field in FIELDS[table][1]])
        self.tree.bind('<Double-1>', lambda event: self.edit())
        self.filter_var.trace_add('write', lambda *args: self.refresh())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        fields = FIELDS[self.table][1]
        refs = {f: choices(self.conn, kind[4:]) for f, _, kind in fields
                if kind.startswith('ref:')}
        query = self.filter_var.get().strip().casefold()
        rows = self.conn.execute(f'SELECT * FROM {self.table} ORDER BY id').fetchall()
        for row in rows:
            vals = [row['id']]
            for field, _, kind in fields:
                val = refs[field].get(row[field], '') if field in refs else row[field]
                vals.append('' if val is None else val)
            if query in ' '.join(map(str, vals)).casefold():
                self.tree.insert('', 'end', iid=str(row['id']), values=vals)
        active = self.conn.execute('SELECT count(*) FROM loans WHERE return_date IS NULL').fetchone()[0]
        self.status.set(f'Показано: {len(self.tree.get_children())} из {len(rows)}  |  Книг у читателей: {active}')

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo('Выберите запись', 'Сначала выберите строку таблицы.', parent=self)
            return None
        return self.conn.execute(f'SELECT * FROM {self.table} WHERE id=?',
                                 (int(selected[0]),)).fetchone()

    def add(self):
        RecordForm(self, self.table)

    def edit(self):
        if self.table == 'hall_types':
            return
        record = self.selected()
        if record:
            RecordForm(self, self.table, record)

    def delete(self):
        record = self.selected()
        if record and messagebox.askyesno('Удаление', 'Удалить выбранную запись?', parent=self):
            try:
                db.delete_record(self.conn, self.table, record['id'])
                self.refresh()
            except sqlite3.Error as exc:
                messagebox.showerror('Удаление невозможно', db.error_message(exc), parent=self)

    def return_book(self):
        record = self.selected()
        if not record:
            return
        if record['return_date']:
            messagebox.showinfo('Возврат', 'Книга уже возвращена.', parent=self)
            return
        value = simpledialog.askstring('Возврат книги', 'Дата возврата (ДД/ММ/ГГГГ):',
                    initialvalue=date.today().strftime('%d/%m/%Y'), parent=self)
        if value is None:
            return
        try:
            db.date_iso(value)
            db.save_record(self.conn, 'loans', {'return_date': value}, record['id'])
            self.refresh()
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('Возврат невозможен', db.error_message(exc), parent=self)

    def show_reports(self):
        self.table = None
        self.clear('Отчеты', 'Год применяется к отчету 1; опорная дата — к возрасту книг и прошлому календарному месяцу. Типы знаний — к отчету 3.')
        bar = ttk.Frame(self.content)
        bar.pack(fill='x')
        self.report_choice = tk.StringVar(value=REPORT_NAMES[0])
        ttk.Combobox(bar, textvariable=self.report_choice, values=REPORT_NAMES,
                     width=37, state='readonly').pack(side='left')
        ttk.Label(bar, text=' Год: ').pack(side='left')
        self.year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(bar, textvariable=self.year_var, width=6).pack(side='left')
        ttk.Label(bar, text=' Опорная дата: ').pack(side='left')
        self.asof_var = tk.StringVar(value=date.today().strftime('%d/%m/%Y'))
        ttk.Entry(bar, textvariable=self.asof_var, width=12).pack(side='left')
        types = ttk.Frame(self.content)
        types.pack(fill='x', pady=12)
        self.type_vars = {}
        for row in self.conn.execute('SELECT * FROM knowledge_types ORDER BY id'):
            var = tk.BooleanVar(value=True)
            self.type_vars[row['id']] = var
            ttk.Checkbutton(types, text=row['name'], variable=var).pack(side='left', padx=(0, 15))
        commands = ttk.Frame(self.content)
        commands.pack(fill='x')
        ttk.Button(commands, text='Сформировать', command=self.run_report).pack(side='left')
        ttk.Button(commands, text='Экспорт CSV', command=self.export).pack(side='right')
        self.make_tree(['Месяц', 'Количество выдач'])
        self.run_report()

    def run_report(self):
        try:
            number = REPORT_NAMES.index(self.report_choice.get()) + 1
            headers, rows = db.report(self.conn, number, self.year_var.get(),
                self.asof_var.get(), [k for k, v in self.type_vars.items() if v.get()])
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror('Ошибка параметров', db.error_message(exc), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        self.headers = headers
        self.tree.configure(columns=list(range(len(headers))))
        for n, label in enumerate(headers):
            self.tree.heading(n, text=label)
            self.tree.column(n, width=230 if label in ('Название', 'Зал', 'Тип зала') else 150,
                             minwidth=65, anchor='w')
        for row in rows:
            self.tree.insert('', 'end', values=row)
        extra = f' | Год: {self.year_var.get()}' if number == 1 else ''
        if number in (2, 4):
            extra = f' | На дату: {self.asof_var.get()}'
        self.status.set(f'Строк: {len(rows)}{extra}')

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, title='Сохранить таблицу',
                    defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(self.headers)
                for iid in self.tree.get_children():
                    writer.writerow(self.tree.item(iid, 'values'))
            messagebox.showinfo('Экспорт', 'Таблица сохранена в CSV.', parent=self)
        except OSError as exc:
            messagebox.showerror('Ошибка сохранения', str(exc), parent=self)

    def close(self):
        self.conn.close()
        self.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Библиотека — вариант 7')
    parser.add_argument('--db', type=Path, default=db.DEFAULT_DB, help='Путь к файлу БД')
    args = parser.parse_args()
    LibraryApp(args.db).mainloop()
