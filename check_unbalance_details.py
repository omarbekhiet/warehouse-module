import sqlite3

db_path = r"database\warehouse.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("="*60)
print("🔎 فحص توازن مجموع المدين والدائن لجميع قيود اليومية")
print("="*60)

# 1. فحص إجمالي المدين والدائن في جدول الحركات
cur.execute("""
    SELECT 
        SUM(debit) as total_debit, 
        SUM(credit) as total_credit,
        SUM(debit) - SUM(credit) as diff
    FROM acc_journal_lines
""")
row = cur.fetchone()
print(f"إجمالي حركة المدين : {row[0]:,.2f}")
print(f"إجمالي حركة الدائن : {row[1]:,.2f}")
print(f"الفرق في قاعدة البيانات: {row[2]:,.2f}")

print("\n" + "="*60)
print("📌 القيود غير المتوازنة (إن وجدت):")
print("="*60)

cur.execute("""
    SELECT entry_id, SUM(debit) as d, SUM(credit) as c, (SUM(debit) - SUM(credit)) as diff
    FROM acc_journal_lines
    GROUP BY entry_id
    HAVING ABS(diff) > 0.01
""")
unbalanced_entries = cur.fetchall()

if not unbalanced_entries:
    print("✅ جميع القيود المحاسبية متوازنة فردياً (المدين = الدائن لكل قيد).")
else:
    for entry in unbalanced_entries:
        print(f"⚠️ القيد رقم {entry[0]}: مدين={entry[1]:,.2f} | دائن={entry[2]:,.2f} | الفرق={entry[3]:,.2f}")

conn.close()