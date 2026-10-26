from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== القيود التي تخص الحسابات 3 و 31 ===")
        rows = conn.execute("""
            SELECT je.entry_no, je.description, jl.account_code, a.name_ar, jl.debit_amount, jl.credit_amount
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE je.status = 'POSTED' AND (jl.account_code = '3' OR jl.account_code = '31')
        """).fetchall()
        
        for r in rows:
            print(f"قيد: {r['entry_no']} | {r['description']} | حساب: {r['account_code']} ({r['name_ar']}) | مدين: {r['debit_amount']:.2f} | دائن: {r['credit_amount']:.2f}")
