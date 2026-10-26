import sqlite3

c = sqlite3.connect('database/warehouse.db')
c.row_factory = sqlite3.Row

print()
print('=' * 70)
print('  فحص شامل للربط بين الحركات والدليل المحاسبي')
print('=' * 70)

# 1. عدد الحسابات
n_acc = c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
print(f'1. عدد الحسابات في الدليل: {n_acc}')

# 2. عدد الأصناف المربوطة بحسابات
n_items = c.execute('SELECT COUNT(*) FROM items WHERE inventory_account IS NOT NULL').fetchone()[0]
print(f'2. عدد الأصناف المربوطة بحسابات: {n_items}')

# 3. عدد قواعد الربط
n_map = c.execute('SELECT COUNT(*) FROM inventory_account_mappings').fetchone()[0]
print(f'3. عدد قواعد الربط: {n_map}')

# 4. عدد الحركات المرحّلة
n_txn = c.execute("SELECT COUNT(*) FROM stock_transactions WHERE status='POSTED'").fetchone()[0]
print(f'4. عدد الحركات المرحّلة: {n_txn}')

# 5. عدد القيود المُنشأة
n_je = c.execute('SELECT COUNT(*) FROM journal_entries').fetchone()[0]
print(f'5. عدد القيود المُنشأة: {n_je}')

# 6. عدد بنود القيود
n_jel = c.execute('SELECT COUNT(*) FROM journal_entry_lines').fetchone()[0]
print(f'6. عدد بنود القيود: {n_jel}')

# 7. فحص توازن القيود
n_bal = c.execute("""
    SELECT COUNT(*) FROM journal_entries
    WHERE ABS(total_debit - total_credit) > 0.01
""").fetchone()[0]
print(f'7. قيود غير متوازنة: {n_bal}')

# 8. فحص بنود بحسابات غير موجودة
n_orphan = c.execute("""
    SELECT COUNT(*) FROM journal_entry_lines jel
    WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.code = jel.account_code)
""").fetchone()[0]
print(f'8. بنود بحسابات غير موجودة: {n_orphan}')

print()
print('=' * 70)

# التقييم
if n_bal == 0 and n_orphan == 0:
    print('  ✅ الربط سليم 100%')
else:
    print('  ⚠️ يحتاج مراجعة:')
    if n_bal > 0:
        print(f'     - {n_bal} قيود غير متوازنة')
    if n_orphan > 0:
        print(f'     - {n_orphan} بنود بحسابات مفقودة')
print('=' * 70)

# عرض تفاصيل قواعد الربط
print()
print('=== قواعد الربط (أول 15) ===')
for r in c.execute("""
    SELECT transaction_type, item_type, debit_account, credit_account 
    FROM inventory_account_mappings 
    ORDER BY transaction_type, item_type
    LIMIT 15
"""):
    tt = r['transaction_type'] or '-'
    it = r['item_type'] or '-'
    print(f'  {tt:20} | {it:15} | {r["debit_account"]:8} --> {r["credit_account"]}')

# عرض عينة من القيود
print()
print('=== عينة من القيود ===')
for r in c.execute("""
    SELECT je.entry_no, je.reference_no, jel.account_code, 
           a.name_ar as account_name, jel.debit_amount, jel.credit_amount
    FROM journal_entries je
    JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
    LEFT JOIN accounts a ON jel.account_code = a.code
    ORDER BY je.id DESC 
    LIMIT 10
"""):
    entry = r['entry_no'] or '-'
    ref = r['reference_no'] or '-'
    code = r['account_code'] or '-'
    name = r['account_name'] or '?'
    d = r['debit_amount'] or 0
    cr = r['credit_amount'] or 0
    print(f'  {entry} | {ref} | {code} {name} | D:{d} C:{cr}')

c.close()
print()
print('Done!')
