from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys

APP = Path(__file__).resolve().parents[1]
PHONE = "+7 (111) 1765880"
sys.path.insert(0,str(APP))
import db


class LibraryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="library-test-")
        self.conn = sqlite3.connect(str(Path(self.temp.name) / "test.db"))
        self.conn.executescript((APP / "schema.sql").read_text(encoding="utf-8"))
        self.conn.executemany("INSERT INTO knowledge_areas VALUES (?,?,?)", [
            (1,"Гуманитарная область",1),(2,"Техническая область",2),(3,"Языки",3)])
        self.conn.executemany("INSERT INTO halls VALUES (?,?,?)", [
            (1,"А — смешанный зал",1),(2,"Б — технический зал",2),
            (3,"В — иностранный зал",3),(4,"Г — пустой зал",1)])
        for i in range(1,9):
            area = 1 if i < 5 else (2 if i < 8 else 3)
            year = 1900 if i < 3 else (1950 if i == 5 else 2000+i)
            self.conn.execute("INSERT INTO books VALUES (?,?,?,?,?,?,?,?)",
                (i,f"Книга {i:02}",f"Автор {i:02}","Москва","Издательство",year,100,area))
            hall = 1 if i < 5 else (2 if i < 8 else 3)
            self.conn.execute("INSERT INTO copies VALUES (?,?,?,?)",(i,f"Э-{i:02}",i,hall))
        self.conn.execute("INSERT INTO copies VALUES (9,'Э-09',1,1)")
        self.conn.execute("INSERT INTO copies VALUES (10,'Э-10',5,1)")
        for i in range(1,5):
            self.conn.execute("INSERT INTO readers VALUES (?,?,?,?,?)",
                (i,f"Ч-{i:02}",f"Читатель {i}","29/02/2000",PHONE))
        self.conn.execute("INSERT INTO librarians VALUES (1,'Библиотекарь',?)",(PHONE,))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def loan(self, copy=1, reader=1, issue="01/09/2026", returned=None):
        return self.conn.execute("INSERT INTO loans(copy_id,reader_id,librarian_id,issue_date,return_date) VALUES (?,?,1,?,?)",
                                 (copy,reader,issue,returned)).lastrowid

    def query(self, number, **params):
        path = next((APP / "queries").glob(f"{number:02}_*.sql"))
        return self.conn.execute(path.read_text(encoding="utf-8"), params).fetchall()

    def rejects(self, sql, params=()):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(sql, params)


class DomainConstraints(LibraryFixture):
    def test_foreign_keys_enabled_and_orphans_rejected(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0],1)
        self.rejects("INSERT INTO copies VALUES (11,'Э-11',999,1)")
        self.rejects("DELETE FROM halls WHERE id=1")

    def test_sixth_active_book_rejected_on_insert(self):
        for i in range(1,6): self.loan(i)
        with self.assertRaises(sqlite3.IntegrityError): self.loan(6)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM loans").fetchone()[0],5)

    def test_reader_transfer_cannot_make_six_active(self):
        for i in range(1,6): self.loan(i)
        loan_id=self.loan(6,2)
        self.rejects("UPDATE loans SET reader_id=1 WHERE id=?",(loan_id,))

    def test_reopening_closed_loan_cannot_make_six_active(self):
        for i in range(1,6): self.loan(i)
        closed=self.loan(6,returned="05/09/2026")
        self.rejects("UPDATE loans SET return_date=NULL WHERE id=?",(closed,))

    def test_return_frees_reader_capacity(self):
        ids=[self.loan(i) for i in range(1,6)]
        self.conn.execute("UPDATE loans SET return_date='02/09/2026' WHERE id=?",(ids[0],))
        self.loan(6,issue="03/09/2026")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM loans WHERE return_date IS NULL").fetchone()[0],5)

    def test_same_edition_cannot_be_issued_twice_to_reader(self):
        self.loan(1)
        with self.assertRaises(sqlite3.IntegrityError): self.loan(9)

    def test_loan_update_cannot_duplicate_edition(self):
        self.loan(1)
        other=self.loan(2)
        self.rejects("UPDATE loans SET copy_id=9 WHERE id=?",(other,))

    def test_closed_duplicate_edition_is_allowed(self):
        self.loan(1,returned="02/09/2026")
        self.loan(9,issue="03/09/2026")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM loans").fetchone()[0],2)

    def test_same_copy_cannot_have_two_active_readers(self):
        self.loan(1)
        with self.assertRaises(sqlite3.IntegrityError): self.loan(1,2)

    def test_update_cannot_take_copy_already_on_loan(self):
        self.loan(1)
        other=self.loan(2,2)
        self.rejects("UPDATE loans SET copy_id=1 WHERE id=?",(other,))

    def test_unchanged_active_loan_is_editable_at_limit(self):
        ids=[self.loan(i) for i in range(1,6)]
        self.conn.execute("UPDATE loans SET issue_date='02/09/2026' WHERE id=?",(ids[0],))

    def test_copy_edition_with_history_cannot_be_reassigned(self):
        self.loan(1,returned="02/09/2026")
        self.rejects("UPDATE copies SET book_id=2 WHERE id=1")

    def test_bibliographic_identity_is_unique(self):
        self.rejects("INSERT INTO books(title,author,publication_place,publisher,publication_year,page_count,knowledge_area_id) SELECT title,author,'Иной город','Иное издательство',publication_year,111,1 FROM books WHERE id=1")
        self.rejects("UPDATE books SET title='Книга 01',author='Автор 01',publication_year=1900 WHERE id=2")

    def test_inventory_and_ticket_unique(self):
        self.rejects("INSERT INTO copies VALUES (11,'Э-01',2,1)")
        self.rejects("UPDATE readers SET ticket_number='Ч-01' WHERE id=2")

    def test_three_fixed_hall_types(self):
        self.assertEqual(self.conn.execute("SELECT count(*) FROM hall_types").fetchone()[0],3)
        self.rejects("INSERT INTO hall_types VALUES (4,'Другой зал')")
        self.rejects("UPDATE hall_types SET name='Другой зал' WHERE id=1")
        self.rejects("DELETE FROM hall_types WHERE id=3")
        self.rejects("UPDATE halls SET hall_type_id=4 WHERE id=4")

    def test_three_knowledge_types_with_editable_names(self):
        self.assertEqual(self.conn.execute("SELECT count(*) FROM knowledge_types").fetchone()[0],3)
        self.rejects("INSERT INTO knowledge_types VALUES (4,'Четвертый тип')")
        self.rejects("UPDATE knowledge_types SET id=4 WHERE id=3")
        self.rejects("DELETE FROM knowledge_types WHERE id=3")
        self.conn.execute("UPDATE knowledge_types SET name='Иное допустимое название' WHERE id=3")

    def test_phone_rejects_invalid_insert_and_update(self):
        bad=["+7 (11) 1765880","+7 (111) 176588","+7 (111) 17658800",
             "+8 (111) 1765880","8(111)1765880","+7 (ABC) 1765880",
             "+7 (111) 176-880","+7 (111) 1765880 ","+7 (111) 176588O",""]
        for phone in bad:
            with self.subTest(phone=phone):
                self.rejects("UPDATE readers SET phone=? WHERE id=1",(phone,))
                self.rejects("INSERT INTO librarians(full_name,phone) VALUES ('Библиотекарь 2',?)",(phone,))

    def test_phone_accepts_exact_format(self):
        self.conn.execute("UPDATE readers SET phone='+7 (999) 1234567' WHERE id=1")
        self.conn.execute("INSERT INTO librarians(full_name,phone) VALUES ('Библиотекарь 2','+7 (000) 0000000')")

    def test_invalid_calendar_dates_rejected_in_all_date_columns(self):
        bad=["29/02/1900","29/02/2025","31/04/2026","31/11/2026","00/01/2026",
             "01/00/2026","01/13/2026","32/01/2026","01/01/0000","1/01/2026",
             "01/1/2026","2026-01-01","01.01.2026","01/01/26","01/01/2026 "]
        lid=self.loan()
        for date in bad:
            with self.subTest(date=date):
                self.rejects("UPDATE readers SET birth_date=? WHERE id=1",(date,))
                self.rejects("UPDATE loans SET issue_date=? WHERE id=?",(date,lid))
                self.rejects("UPDATE loans SET return_date=? WHERE id=?",(date,lid))
                self.rejects("INSERT INTO visits(reader_id,hall_id,visit_date) VALUES (1,1,?)",(date,))

    def test_gregorian_leap_dates_are_valid(self):
        for date in ("29/02/2000","29/02/2024","29/02/2400","28/02/1900","31/12/9999","01/01/0001"):
            with self.subTest(date=date):
                self.conn.execute("UPDATE readers SET birth_date=? WHERE id=1",(date,))
                self.conn.execute("INSERT INTO visits(reader_id,hall_id,visit_date) VALUES (1,1,?)",(date,))

    def test_return_before_issue_rejected_on_insert(self):
        for issue,returned in (("01/10/2026","30/09/2026"),("01/01/2026","31/12/2025"),("11/09/2026","10/09/2026")):
            with self.subTest(issue=issue,returned=returned):
                with self.assertRaises(sqlite3.IntegrityError): self.loan(issue=issue,returned=returned)

    def test_return_before_issue_rejected_on_update(self):
        lid=self.loan(issue="01/10/2026")
        self.rejects("UPDATE loans SET return_date='30/09/2026' WHERE id=?",(lid,))
        self.conn.execute("UPDATE loans SET return_date='01/10/2026' WHERE id=?",(lid,))
        self.rejects("UPDATE loans SET issue_date='02/10/2026' WHERE id=?",(lid,))

    def test_same_day_return_valid(self):
        self.loan(issue="31/12/2026",returned="31/12/2026")

    def test_numeric_and_nonblank_fields(self):
        for field,value in (("publication_year",0),("publication_year",10000),("publication_year",2000.5),
                            ("page_count",0),("page_count",-1),("page_count",10.5),("title"," ")):
            with self.subTest(field=field,value=value):
                self.rejects(f"UPDATE books SET {field}=? WHERE id=1",(value,))


class RequiredReports(LibraryFixture):
    def test_monthly_report_zero_fills_all_twelve_months(self):
        self.assertEqual(self.query(1,year=2026),[(i,0) for i in range(1,13)])

    def test_monthly_report_includes_year_boundaries(self):
        dates=["31/12/2025","01/01/2026","31/01/2026","01/02/2026","31/12/2026","01/01/2027"]
        for date in dates: self.loan(issue=date,returned=date)
        result=dict(self.query(1,year=2026))
        self.assertEqual(sum(result.values()),4)
        self.assertEqual((result[1],result[2],result[12]),(2,1,1))

    def test_oldest_books_keeps_all_ties_deduplicates_copies(self):
        rows=self.query(2,current_year=2026)
        a=[r for r in rows if r[0]=="А — смешанный зал"]
        self.assertEqual({r[1] for r in a},{"Книга 01","Книга 02"})
        self.assertEqual(len(a),2)
        self.assertEqual({r[4] for r in a},{126})
        self.assertFalse(any(r[0]=="Г — пустой зал" for r in rows))
        self.assertEqual(next(r for r in rows if r[0]=="Б — технический зал")[1],"Книга 05")

    def test_halls_only_selected_multiple_types_subset_semantics(self):
        rows=self.query(3,type1=1,type2=2,type3=0)
        self.assertEqual({r[0] for r in rows},{"А — смешанный зал","Б — технический зал"})
        self.assertEqual(next(r[2] for r in rows if r[0]=="А — смешанный зал"),6)

    def test_halls_single_type_excludes_mixed_and_empty_halls(self):
        self.assertEqual([r[0] for r in self.query(3,type1=0,type2=2,type3=0)],["Б — технический зал"])
        self.assertEqual(self.query(3,type1=1,type2=0,type3=0),[])

    def test_halls_no_types_returns_none(self):
        self.assertEqual(self.query(3,type1=0,type2=0,type3=0),[])

    def test_halls_all_types_returns_all_nonempty_halls(self):
        self.assertEqual(len(self.query(3,type1=1,type2=2,type3=3)),3)

    def test_top_five_previous_calendar_month_year_rollover(self):
        for copy in range(1,8):
            for day in range(1,9-copy):
                date=f"{day:02}/12/2025"
                self.loan(copy=copy,issue=date,returned=date)
        self.loan(copy=1,issue="31/12/2025",returned="31/12/2025")
        for date in ("30/11/2025","01/01/2026","31/01/2026"):
            for _ in range(10): self.loan(copy=8,issue=date,returned=date)
        rows=self.query(4,as_of="2026-01-15")
        self.assertEqual([r[0] for r in rows],[f"Книга {i:02}" for i in range(1,6)])
        self.assertEqual([r[3] for r in rows],[8,6,5,4,3])

    def test_top_report_counts_edition_across_copies_and_ties_stably(self):
        for copy in (1,9,2,2,3): self.loan(copy=copy,issue="01/09/2026",returned="01/09/2026")
        rows=self.query(4,as_of="2026-10-04")
        self.assertEqual([(r[0],r[3]) for r in rows],[("Книга 01",2),("Книга 02",2),("Книга 03",1)])

    def test_top_previous_month_includes_last_leap_day(self):
        for date in ("31/01/2024","01/02/2024","29/02/2024","01/03/2024"):
            self.loan(issue=date,returned=date)
        self.assertEqual(self.query(4,as_of="2024-03-01")[0][3],2)

    def test_top_report_empty_month_has_no_fabricated_books(self):
        self.assertEqual(self.query(4,as_of="2026-10-04"),[])


class ServiceLayer(LibraryFixture):
    def test_form_record_add_edit_delete_and_reopen(self):
        self.conn.row_factory=sqlite3.Row
        rid=db.save_record(self.conn,"readers",dict(ticket_number="QA-1",full_name="Тестовый читатель",birth_date="15/01/2001",phone=PHONE))
        db.save_record(self.conn,"readers",{"full_name":"Исправленный читатель"},rid)
        self.assertEqual(self.conn.execute("SELECT full_name FROM readers WHERE id=?",(rid,)).fetchone()[0],"Исправленный читатель")
        reopened=db.connect(Path(self.temp.name)/"test.db")
        try:
            self.assertEqual(reopened.execute("SELECT full_name FROM readers WHERE id=?",(rid,)).fetchone()[0],"Исправленный читатель")
            self.assertEqual(reopened.execute("PRAGMA foreign_keys").fetchone()[0],1)
        finally: reopened.close()
        db.delete_record(self.conn,"readers",rid)
        self.assertIsNone(self.conn.execute("SELECT id FROM readers WHERE id=?",(rid,)).fetchone())

    def test_failed_form_save_rolls_back_without_losing_prior_record(self):
        self.conn.row_factory=sqlite3.Row
        with self.assertRaises(sqlite3.IntegrityError):
            db.save_record(self.conn,"readers",{"phone":"invalid"},1)
        self.assertEqual(self.conn.execute("SELECT phone FROM readers WHERE id=1").fetchone()[0],PHONE)
        db.save_record(self.conn,"readers",{"full_name":"Успешное исправление"},1)

    def test_form_values_are_parameters(self):
        self.conn.row_factory=sqlite3.Row
        value="Имя'); DROP TABLE books; --"
        db.save_record(self.conn,"readers",{"full_name":value},1)
        self.assertEqual(self.conn.execute("SELECT full_name FROM readers WHERE id=1").fetchone()[0],value)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM books").fetchone()[0],8)

    def test_unknown_table_and_field_rejected(self):
        self.conn.row_factory=sqlite3.Row
        with self.assertRaises(ValueError): db.save_record(self.conn,"unknown",{"name":"x"})
        with self.assertRaises(ValueError): db.save_record(self.conn,"readers",{"unknown":"x"})
        with self.assertRaises(ValueError): db.save_record(self.conn,"readers",{"id":12})

    def test_report_api_validates_user_parameters(self):
        for kwargs in ({"number":0},{"number":5},{"number":1,"year":0},
                       {"number":4,"as_of":"29/02/2025"},{"number":4,"as_of":"1/10/2026"},
                       {"number":3,"type_ids":[]},{"number":3,"type_ids":[4]}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError): db.report(self.conn,**kwargs)

    def test_report_api_converts_dates_and_multiselection(self):
        self.loan(issue="31/12/2025",returned="31/12/2025")
        headers,rows=db.report(self.conn,4,as_of="15/01/2026")
        self.assertEqual(len(headers),4)
        self.assertEqual(rows[0][3],1)
        _,rows=db.report(self.conn,3,type_ids=[2,1,2])
        self.assertEqual({r[0] for r in rows},{"А — смешанный зал","Б — технический зал"})

    def test_existing_database_is_never_reinitialized(self):
        path=Path(self.temp.name)/"test.db"
        self.assertFalse(db.initialize(path,demo=True))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM books").fetchone()[0],8)

    def test_new_database_contains_three_types_and_demo_data(self):
        path=Path(self.temp.name)/"new_demo.db"
        self.assertTrue(db.initialize(path,demo=True))
        conn=db.connect(path)
        try:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(),[])
            self.assertEqual(conn.execute("SELECT count(*) FROM books").fetchone()[0],10)
            _,rows=db.report(conn,1,year=2026,as_of="04/10/2026")
            self.assertEqual(len(rows),12)
            self.assertEqual(dict(rows)[9],22)
            _,rows=db.report(conn,4,as_of="04/10/2026")
            self.assertEqual([r[3] for r in rows],[6,5,4,3,2])
        finally: conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
