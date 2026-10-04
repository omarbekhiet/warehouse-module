import sqlite3
conn = sqlite3.connect('database/warehouse.db')
conn.execute("DELETE FROM inventory_count_lines")
conn.execute("DELETE FROM inventory_counts")
conn.commit()
print("Counts cleared")
conn.close()
