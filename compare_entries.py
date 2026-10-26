import sqlite3

# مسار قاعدة البيانات الحالية والنسخة الاحتياطية
DB_CURRENT = "database/warehouse.db"
DB_OLD = "database/warehouse.db.bak_before_recode"

def compare_entries():
    conn_cur = sqlite3.connect(DB_CURRENT)
    conn_cur.row_factory = sqlite3.Row
    cur_cur = conn_cur.cursor()

    conn_old = sqlite3.connect(DB_OLD)
    conn_old.row_factory = sqlite3.Row
    cur_old = conn_old.cursor()

    try:
        print("=== مقارنة القيود (النسخة القديمة vs الجديدة) ===")
        print(f"{'القيد':<10} | {'الحساب القديم':<15} | {'الحساب الجديد':<15} | {'المدين':<10} | {'الدائن':<10}")
        print("-" * 75)

        # جلب أول 15 قيداً من النسخة القديمة
        old_rows = cur_old.execute("""
            SELECT je.entry_no, jl.account_code, jl.debit_amount, jl.credit_amount
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            ORDER BY je.id, jl.line_no
            LIMIT 15
        """).fetchall()

        for old_row in old_rows:
            entry_no = old_row['entry_no']
            old_code = old_row['account_code']
            debit = old_row['debit_amount']
            credit = old_row['credit_amount']

            # البحث عن القيد المقابل في النسخة الجديدة
            new_row = cur_cur.execute("""
                SELECT jl.account_code
                FROM journal_entry_lines jl
                JOIN journal_entries je ON jl.journal_entry_id = je.id
                WHERE je.entry_no = ? AND jl.debit_amount = ? AND jl.credit_amount = ?
                LIMIT 1
            """, (entry_no, debit, credit)).fetchone()

            new_code = new_row['account_code'] if new_row else '❌ غير موجود'

            print(f"{entry_no:<10} | {old_code:<15} | {new_code:<15} | {debit:<10.2f} | {credit:<10.2f}")

        print("\n=== التحقق من إجمالي المبالغ ===")
        old_totals = cur_old.execute("SELECT SUM(debit_amount) as d, SUM(credit_amount) as c FROM journal_entry_lines").fetchone()
        new_totals = cur_cur.execute("SELECT SUM(debit_amount) as d, SUM(credit_amount) as c FROM journal_entry_lines").fetchone()

        print(f"إجمالي المدين (قديم): {old_totals['d']:.2f} | (جديد): {new_totals['d']:.2f}")
        print(f"إجمالي الدائن (قديم): {old_totals['c']:.2f} | (جديد): {new_totals['c']:.2f}")
        print(f"الفرق (قديم): {old_totals['d'] - old_totals['c']:.2f} | (جديد): {new_totals['d'] - new_totals['c']:.2f}")

    except Exception as e:
        print(f"❌ خطأ: {e}")
    finally:
        conn_cur.close()
        conn_old.close()

if __name__ == "__main__":
    compare_entries()
