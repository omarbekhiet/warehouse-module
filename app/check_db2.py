import sqlite3

conn = sqlite3.connect(r'..\database\warehouse.db')
cursor = conn.cursor()

print('--- أسماء الأعمدة في جدول journal_entries ---')
cursor.execute("PRAGMA table_info(journal_entries);")
columns = [col[1] for col in cursor.fetchall()]
print(columns)

print('\n--- البحث عن القيود اللي فيها إهلاك (بناءً على أول عمود للتاريخ) ---')
# بنجرب نلاقي عمود التاريخ الحقيقي
date_col = 'date'
if 'entry_date' in columns: date_col = 'entry_date'
elif 'created_at' in columns: date_col = 'created_at'

try:
    query = f"SELECT id, {date_col}, description FROM journal_entries WHERE description LIKE '%إهلاك%';"
    cursor.execute(query)
    rows = cursor.fetchall()
    print(f'عدد القيود اللي فيها إهلاك: {len(rows)}')
    for r in rows:
        print(' ', r)
except Exception as e:
    print(f'خطأ: {e}')

conn.close()
