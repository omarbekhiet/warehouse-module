import sqlite3

def fix_depreciation():
    # الاتصال بقاعدة البيانات في مجلد database
    db_path = 'database/warehouse.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- جارٍ فحص قيود الإهلاك الحالية ---")
    cursor.execute("""
        SELECT id, entry_no, entry_date, description, total_debit 
        FROM journal_entries 
        WHERE description LIKE '%إهلاك%' OR description LIKE '%Depreciation%' OR description LIKE '%هلاك%'
    """)
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"ID: {row[0]} | رقم القيّد: {row[1]} | التاريخ: {row[2]} | الوصف: {row[3]} | القيمة: {row[4]}")

    # يمكنك هنا تعديل القيود أو ترك قيد واحد صحيح بقيمة 325,000 وحذف الباقي المكرر
    # بناءً على الفحص، لو أردت تحديث أول قيد ليصبح 325000 وحذف القيود المكررة الزائدة:
    if rows:
        first_id = rows[0][0]
        # تحديث القيد الأول للقيمة الصحيحة 325000
        cursor.execute("UPDATE journal_entries SET total_debit = 325000, total_credit = 325000 WHERE id = ?", (first_id,))
        
        # حذف أي قيود إهلاك مكررة أخرى إذا وجدت
        if len(rows) > 1:
            duplicate_ids = [r[0] for r in rows[1:]]
            cursor.executemany("DELETE FROM journal_entries WHERE id = ?", [(i,) for i in duplicate_ids])
            # حذف السطور المرتبطة بها في journal_entry_lines
            for d_id in duplicate_ids:
                cursor.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id = ?", (d_id,))
            print(f"تم حذف {len(duplicate_ids)} قيود إهلاك مكررة بنجاح.")

        conn.commit()
        print("--- تم تصحيح وتحديث قيمة الإهلاك إلى 325,000 بنجاح ---")
    else:
        print("لم يتم العثور على قيود إهلاك مطابقة.")

    conn.close()

if __name__ == '__main__':
    fix_depreciation()