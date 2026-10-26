from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== الحسابات التي عليها حركات مباشرة (قيود) ===")
        print(f"{'الكود':<10} | {'الاسم':<30} | {'المستوى':<8} | {'الرصيد':<15}")
        print("-" * 75)
        
        q = """
            SELECT CAST(jl.account_code AS TEXT) as code, a.name_ar, a.level,
                   SUM(jl.debit_amount) - SUM(jl.credit_amount) as balance
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE je.status = 'POSTED' 
            GROUP BY jl.account_code
            HAVING balance != 0
            ORDER BY a.level, jl.account_code
        """
        
        rows = conn.execute(q).fetchall()
        for r in rows:
            lvl = r['level'] if r['level'] else 'غير موجود'
            print(f"{r['code']:<10} | {r['name_ar']:<30} | {lvl:<8} | {r['balance']:>15,.2f}")
        
        print(f"\nإجمالي الحسابات التي عليها حركات: {len(rows)}")
