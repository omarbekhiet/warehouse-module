# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = "database/warehouse.db"

def cleanup_entry_23():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # البحث عن القيد رقم 23
        entry = cur.execute("SELECT id, entry_no FROM journal_entries WHERE id = 23").fetchone()
        
        if not entry:
            print("⚠️ القيد رقم 23 غير موجود.")
            return
            
        print(f"🔍 وجدت القيد: {entry['entry_no']} (ID: 23)")
        
        # حذف السطور
        cur.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id = 23")
        deleted_lines = cur.rowcount
        
        # حذف القيد الرئيسي
        cur.execute("DELETE FROM journal_entries WHERE id = 23")
        deleted_entry = cur.rowcount
        
        conn.commit()
        print(f"✅ تم حذف القيد {entry['entry_no']} و {deleted_lines} سطر.")
        
        # التحقق من التوازن
        res = cur.execute("SELECT SUM(debit_amount) as d, SUM(credit_amount) as c FROM journal_entry_lines").fetchone()
        print(f"\n📊 التحقق من التوازن:")
        print(f"  إجمالي المدين: {res['d']:.2f}")
        print(f"  إجمالي الدائن: {res['c']:.2f}")
        print(f"  الفرق: {(res['d'] - res['c']):.2f}")
        
        if abs(res['d'] - res['c']) < 0.01:
            print("✅ التوازن سليم!")
        else:
            print("⚠️ لا يزال هناك اختلال في التوازن.")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_entry_23()
