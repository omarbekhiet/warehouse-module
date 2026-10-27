import sqlite3

conn = sqlite3.connect('database/warehouse')
cursor = conn.cursor()

# عرض قيود الإهلاك الحالية للتأكد منها
cursor.execute("SELECT id, entry_no, entry_date, total_debit FROM journal_entries WHERE description LIKE '%إهلاك%' OR description LIKE '%Depreciation%'")
print("قيود الإهلاك الحالية:", cursor.fetchall())

# يمكنك هنا تعديل القيمة أو حذف القيود المكررة الزائدة
# مثال: تعديل إجمالي المدين/الدائن للقيد الصحيح ليصبح 325,000 بدلاً من القيمة المكررة
# أو حذف القيود الزائدة وتحديث الأرقام

conn.commit()
conn.close()
print("تم الفحص.")