from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== جميع الحسابات في الدليل ===")
        print(f"{'الكود':<15} | {'الاسم':<30} | {'الأب':<15} | {'المستوى':<8}")
        print("-" * 80)
        
        rows = conn.execute("SELECT code, name_ar, parent_code, level FROM accounts ORDER BY code").fetchall()
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"{r['code']:<15} | {r['name_ar']:<30} | {parent:<15} | {r['level']:<8}")
        
        print(f"\nإجمالي الحسابات: {len(rows)}")
