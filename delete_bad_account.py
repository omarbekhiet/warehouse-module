# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = "database/warehouse.db"

def cleanup_bad_account():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # البحث عن القيود التي تحتوي على الحساب 5299
        rows = cur.execute("SELECT journal_entry_id, debit_amount, credit_amount FROM journal_entry_lines WHERE account_code = '5299'").fetchall()
        
        if not rows:
            print("⚠️ لا توجد قيود على الحساب 5299.")
            return
            
        print(f"🔍 وجدت {len(rows)} قيد على الحساب 5299:")
        for r in rows:
            print(f"  القيد: {r['journal_entry_id']} | مدين: {r['debit_amount']} | دائن: {r['credit_amount']}")
        
        # حذف هذه القيود
        cur.execute("DELETE FROM journal_entry_lines WHERE account_code = '5299'")
        deleted = cur.rowcount
        conn.commit()
        print(f"✅ تم حذف {deleted} سطر قيد على الحساب 5299.")
        
        # التحقق من التوازن
        res = cur.execute("SELECT SUM(debit_amount) as d, SUM(credit_amount) as c FROM journal_entry_lines").fetchone()
        print(f"\n📊 التحقق من التوازن:")
        print(f"  إجمالي المدين: {res['d']:.2f}")
        print(f"  إجمالي الدائن: {res['c']:.2f}")
        print(f"  الفرق: {(res['d'] - res['c']):.2f}")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_bad_account()
