import sqlite3
import os

src = 'database/warehouse.db'
dst = 'database/warehouse_template.db'

# نسخة من قاعدة البيانات الحالية
if os.path.exists(src):
    import shutil
    shutil.copy2(src, dst)
    print(f"OK: نسخة محفوظة في {dst}")
    print(f"الحجم: {os.path.getsize(dst) / 1024:.1f} KB")
else:
    print("ERROR: لم يتم العثور على database/warehouse.db")
