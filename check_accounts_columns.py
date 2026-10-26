from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== أعمدة جدول الحسابات ===")
        cols = conn.execute("PRAGMA table_info(accounts)").fetchall()
        for c in cols:
            print(f"العمود: {c['name']} | النوع: {c['type']}")
        
        print("\n=== عينة من البيانات (لنرى قيم الأعمدة) ===")
        rows = conn.execute("SELECT code, name_ar, financial_statement, bs_group, pl_group FROM accounts LIMIT 10").fetchall()
        for r in rows:
            print(f"كود: {r['code']} | اسم: {r['name_ar']} | financial_statement: {r['financial_statement']} | bs_group: {r['bs_group']} | pl_group: {r['pl_group']}")
