from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== الحسابات التي عليها حركات مباشرة (المستوى 1 و 2) ===")
        print(f"{'الكود':<10} | {'الاسم':<30} | {'المستوى':<8} | {'الرصيد':<15}")
        print("-" * 75)
        
        q = """
            SELECT CAST(jl.account_code AS TEXT) as code, a.name_ar, a.level,
                   SUM(jl.debit_amount) - SUM(jl.credit_amount) as balance
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE je.status = 'POSTED' 
              AND (a.level = 'L1' OR a.level = 'L2')
            GROUP BY jl.account_code
            HAVING balance != 0
            ORDER BY a.level, jl.account_code
        """
        
        rows = conn.execute(q).fetchall()
        for r in rows:
            code = r['code'] if r['code'] else '—'
            name = r['name_ar'] if r['name_ar'] else '⚠️ غير موجود في الدليل'
            lvl = r['level'] if r['level'] else '—'
            balance = r['balance'] if r['balance'] else 0.0
            print(f"{code:<10} | {name:<30} | {lvl:<8} | {balance:>15,.2f}")
        
        print(f"\nإجمالي الحسابات (L1, L2) التي عليها حركات: {len(rows)}")
