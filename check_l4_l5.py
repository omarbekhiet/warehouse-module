from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== الحسابات التي مستواها L4 أو L5 (للتأكد) ===")
        rows = conn.execute("""
            SELECT code, name_ar, parent_code, level 
            FROM accounts 
            WHERE level IN ('L4', 'L5') 
            ORDER BY code
        """).fetchall()
        
        for r in rows:
            parent = r['parent_code'] if r['parent_code'] else '—'
            print(f"كود: {r['code']:<12} | اسم: {r['name_ar']:<30} | الأب: {parent:<10} | المستوى: {r['level']}")
        
        print(f"\nإجمالي الحسابات في L4 و L5: {len(rows)}")
