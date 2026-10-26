from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=" * 70)
        print(f"{'المستوى':<10} | {'إجمالي المدين':<20} | {'إجمالي الدائن':<20} | {'الفرق':<15}")
        print("=" * 70)

        for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
            # جلب الحسابات التي تنتمي لهذا المستوى فقط
            q = """
                SELECT 
                    COALESCE(SUM(jl.debit_amount), 0) as total_debit,
                    COALESCE(SUM(jl.credit_amount), 0) as total_credit
                FROM journal_entry_lines jl
                JOIN journal_entries je ON jl.journal_entry_id = je.id
                JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
                WHERE je.status = 'POSTED' AND a.level = ?
            """
            res = conn.execute(q, (level,)).fetchone()
            
            total_d = res['total_debit'] if res else 0.0
            total_c = res['total_credit'] if res else 0.0
            diff = total_d - total_c
            
            print(f"{level:<10} | {total_d:>20,.2f} | {total_c:>20,.2f} | {diff:>15,.2f}")
        
        print("=" * 70)
        
        # إجمالي كل المستويات معاً
        q_all = """
            SELECT 
                COALESCE(SUM(jl.debit_amount), 0) as total_debit,
                COALESCE(SUM(jl.credit_amount), 0) as total_credit
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            WHERE je.status = 'POSTED'
        """
        res_all = conn.execute(q_all).fetchone()
        print(f"{'الإجمالي':<10} | {res_all['total_debit']:>20,.2f} | {res_all['total_credit']:>20,.2f} | {res_all['total_debit'] - res_all['total_credit']:>15,.2f}")
        print("=" * 70)
