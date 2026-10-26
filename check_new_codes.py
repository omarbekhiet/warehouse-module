from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== عينة من الحسابات بعد إعادة الترميز (الأصول) ===")
        print(f"{'الكود':<10} | {'الاسم':<30} | {'الأب':<10} | {'المستوى':<8}")
        print("-" * 65)
        
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts WHERE code LIKE '1%' ORDER BY code LIMIT 40").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<10} | {r['name_ar']:<30} | {parent:<10} | {r['level']:<8}")

        print("\n=== عينة من الحسابات بعد إعادة الترميز (الخصوم) ===")
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts WHERE code LIKE '2%' ORDER BY code LIMIT 20").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<10} | {r['name_ar']:<30} | {parent:<10} | {r['level']:<8}")

        print("\n=== عينة من الحسابات بعد إعادة الترميز (الإيرادات) ===")
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts WHERE code LIKE '4%' ORDER BY code LIMIT 15").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<10} | {r['name_ar']:<30} | {parent:<10} | {r['level']:<8}")

        print("\n=== عينة من الحسابات بعد إعادة الترميز (حقوق الملكية) ===")
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts WHERE code LIKE '8%' ORDER BY code LIMIT 15").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<10} | {r['name_ar']:<30} | {parent:<10} | {r['level']:<8}")
