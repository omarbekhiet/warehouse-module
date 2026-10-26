from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== الحسابات التي عليها حركات (تكاليف 3) ===")
        rows = conn.execute("""
            SELECT jl.account_code, a.name_ar, a.level, SUM(jl.debit_amount) - SUM(jl.credit_amount) as balance
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE je.status = 'POSTED' AND jl.account_code LIKE '3%'
            GROUP BY jl.account_code
            ORDER BY jl.account_code
        """).fetchall()
        
        for r in rows:
            print(f"كود: {r['account_code']:<10} | اسم: {r['name_ar']:<30} | مستوى: {r['level']:<5} | رصيد: {r['balance']:.2f}")
