from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=" * 80)
        print(f"{'المستوى':<10} | {'إجمالي المدين (بعد التجميع)':<25} | {'إجمالي الدائن (بعد التجميع)':<25} | {'الفرق':<15}")
        print("=" * 80)

        for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
            # 1. جلب الحسابات التي تنتمي لهذا المستوى فقط
            accounts = conn.execute("""
                SELECT code, name_ar, parent_code, level 
                FROM accounts 
                WHERE level = ?
            """, (level,)).fetchall()
            
            if not accounts:
                print(f"{level:<10} | {'لا توجد حسابات':<25} | {'لا توجد حسابات':<25} | {'-':<15}")
                continue

            # 2. جلب الأرصدة المباشرة لهذه الحسابات
            total_d = 0.0
            total_c = 0.0
            for acc in accounts:
                code = str(acc['code']).strip()
                res = conn.execute("""
                    SELECT COALESCE(SUM(debit_amount), 0) as d, COALESCE(SUM(credit_amount), 0) as c
                    FROM journal_entry_lines jl
                    JOIN journal_entries je ON jl.journal_entry_id = je.id
                    WHERE je.status = 'POSTED' AND jl.account_code = ?
                """, (code,)).fetchone()
                
                total_d += float(res['d']) if res else 0.0
                total_c += float(res['c']) if res else 0.0

            diff = total_d - total_c
            print(f"{level:<10} | {total_d:>25,.2f} | {total_c:>25,.2f} | {diff:>15,.2f}")
        
        print("=" * 80)
        
        # إجمالي كل المستويات
        res_all = conn.execute("""
            SELECT COALESCE(SUM(debit_amount), 0) as d, COALESCE(SUM(credit_amount), 0) as c
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            WHERE je.status = 'POSTED'
        """).fetchone()
        
        print(f"{'الإجمالي':<10} | {res_all['d']:>25,.2f} | {res_all['c']:>25,.2f} | {res_all['d'] - res_all['c']:>15,.2f}")
        print("=" * 80)
