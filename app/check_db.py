import sqlite3

conn = sqlite3.connect(r'..\database\warehouse.db')
cursor = conn.cursor()

print('--- 1. الجداول الموجودة في الداتابيز ---')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
for t in tables:
    print(' -', t)

print('\n--- 2. البحث عن القيود اللي فيها إهلاك ---')
# بنجرب ندور في الجداول المحتملة
possible_tables = ['journal_entries', 'acc_journal_entries', 'entries']
for t in possible_tables:
    if t in tables:
        print(f'البحث في جدول: {t}')
        try:
            cursor.execute(f"SELECT id, date, description FROM {t} WHERE description LIKE '%إهلاك%';")
            rows = cursor.fetchall()
            print(f'  عدد القيود اللي فيها إهلاك: {len(rows)}')
            for r in rows:
                print('  ', r)
        except Exception as e:
            print(f'  خطأ في القراءة: {e}')

conn.close()
