# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = "database/warehouse.db"

def cleanup_entries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # قائمة القيود التي نريد حذفها
        entries_to_delete = ['JE-2026-000002', 'JE-2026-000007', 'JE-TEST-003']
        
        for entry_no in entries_to_delete:
            # البحث عن القيد
            entry = cur.execute("SELECT id FROM journal_entries WHERE entry_no = ?", (entry_no,)).fetchone()
            if entry:
                entry_id = entry['id']
                # حذف السطور
                cur.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id = ?", (entry_id,))
                # حذف القيد
                cur.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
                print(f"✅ تم حذف القيد: {entry_no}")
            else:
                print(f"⚠️ القيد {entry_no} غير موجود.")

        conn.commit()
        print("\n🎉 تم الانتهاء من تنظيف القيود.")
        
        # التحقق من عدم وجود قيود على الحسابات الوسيطة
        res = cur.execute("""
            SELECT COUNT(*) as cnt FROM journal_entry_lines 
            WHERE account_code IN ('3', '31')
        """).fetchone()
        if res['cnt'] == 0:
            print("✅ لا توجد قيود على الحسابات الوسيطة (3، 31).")
        else:
            print(f"⚠️ لا يزال هناك {res['cnt']} قيد على الحسابات الوسيطة.")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_entries()
