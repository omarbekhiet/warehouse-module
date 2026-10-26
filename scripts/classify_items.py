import sqlite3

DB = 'J:/warehouse-module/database/warehouse.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# تحديث التصنيف حسب النوع
updates = [
    ("RAW_MATERIAL",    "OPERATING"),
    ("FINISHED_GOODS",  "OPERATING"),
    ("MERCHANDISE",     "OPERATING"),
    ("SUPPLIES",        "NON_OPERATING"),
    ("ASSET",           "CAPITAL"),
    ("SERVICE",         "OPERATING"),
]

print("=== تحديث التصنيف حسب النوع ===")
for item_type, op_type in updates:
    cur.execute("UPDATE items SET operating_type=? WHERE item_type=? AND (operating_type IS NULL OR operating_type='')", (op_type, item_type))
    print(f"  {item_type} -> {op_type}: {cur.rowcount} rows")

conn.commit()

print()
print("=== التصنيف النهائي ===")
for r in cur.execute("SELECT operating_type, COUNT(*) FROM items GROUP BY operating_type"):
    print(f"  {r[0]}: {r[1]} صنف")

print()
print("=== المخزون حسب النوع ===")
for r in cur.execute("""
    SELECT i.operating_type, COUNT(DISTINCT i.id),
           COALESCE(SUM(sb.total_value), 0)
    FROM items i
    LEFT JOIN stock_balances sb ON i.id = sb.item_id
    GROUP BY i.operating_type
"""):
    print(f"  {r[0]}: {r[1]} صنف — {r[2]:,.2f}")

conn.close()
print()
print("Done!")
