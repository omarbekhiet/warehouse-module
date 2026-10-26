from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== فحص بنية الحسابات (الأصول) ===")
        print(f"{'كود':<10} | {'الاسم':<25} | {'الأب':<10} | {'المستوى':<8}")
        print("-" * 60)
        
        # جلب كل حسابات الأصول
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts WHERE code LIKE '1%' ORDER BY code LIMIT 30").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<10} | {r['name_ar']:<25} | {parent:<10} | {r['level']:<8}")
