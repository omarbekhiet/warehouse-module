from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== الحسابات التي عليها حركات ===")
        rows = conn.execute("""
            SELECT DISTINCT CAST(jl.account_code AS TEXT) as code, a.name_ar, a.level
            FROM journal_entry_lines jl
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE jl.account_code IS NOT NULL AND jl.account_code LIKE '1%'
            LIMIT 20
        """).fetchall()
        for r in rows:
            print(f"كود: {r['code']} | اسم: {r['name_ar']} | مستوى: {r['level']}")
