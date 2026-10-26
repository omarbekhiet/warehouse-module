"""
إضافة بيانات تجريبية للاختبار
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'warehouse.db')
print(f"Database: {DB_PATH}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ============================================
# 1. فحص البيانات الحالية
# ============================================
print("=" * 60)
print("📊 فحص البيانات")
print("=" * 60)

cur.execute("SELECT id, name_ar FROM suppliers LIMIT 3")
suppliers = [dict(r) for r in cur.fetchall()]
print(f"  الموردين: {len(suppliers)}")

cur.execute("SELECT id, name_ar FROM customers LIMIT 3")
customers = [dict(r) for r in cur.fetchall()]
print(f"  العملاء: {len(customers)}")

cur.execute("SELECT id, name_ar, current_balance FROM cash_boxes LIMIT 3")
boxes = [dict(r) for r in cur.fetchall()]
print(f"  الخزائن: {len(boxes)}")

# ============================================
# 2. إنشاء خزينة لو مش موجودة
# ============================================
if not boxes:
    print("\n📦 إنشاء خزينة اختبار...")
    cur.execute("""
        INSERT INTO cash_boxes 
        (code, name_ar, box_type, account_code, opening_balance, current_balance, is_active)
        VALUES ('TEST-01', 'الخزينة الرئيسية', 'MAIN', '1211', 100000, 100000, 1)
    """)
    box_id = cur.lastrowid
    print(f"  ✅ خزينة: id={box_id}")
else:
    box_id = boxes[0]['id']
    print(f"\n📌 استخدام خزينة موجودة: {boxes[0]['name_ar']}")

# ============================================
# 3. إنشاء تصنيف مصروفات لو مش موجود
# ============================================
cur.execute("SELECT id, name_ar FROM expense_categories LIMIT 1")
cat = cur.fetchone()

if not cat:
    print("\n🏷️ إنشاء تصنيف مصروفات...")
    cur.execute("""
        INSERT INTO expense_categories 
        (code, name_ar, account_code, is_active)
        VALUES ('EXP-TEST', 'مصروفات إدارية', '5299', 1)
    """)
    cat_id = cur.lastrowid
    print(f"  ✅ تصنيف: id={cat_id}")
else:
    cat_id = cat['id']
    print(f"\n📌 استخدام تصنيف موجود: {cat['name_ar']}")

# ============================================
# 4. إضافة دفعة مورد
# ============================================
if suppliers:
    print("\n" + "=" * 60)
    print("💳 إضافة دفعة مورد")
    print("=" * 60)
    
    supplier_id = suppliers[0]['id']
    payment_no = "PAY-TEST-001"
    
    # تحقق إنها مش موجودة
    cur.execute("SELECT id FROM supplier_payments WHERE payment_no = ?", (payment_no,))
    existing = cur.fetchone()
    
    if not existing:
        # 1. القيد
        cur.execute("""
            INSERT INTO journal_entries 
            (entry_no, entry_date, reference_type, reference_no, description, status, total_debit, total_credit)
            VALUES ('JE-TEST-001', '2026-10-07', 'SUPPLIER_PAYMENT', ?, 'دفعة مورد اختبار', 'POSTED', 1000, 1000)
        """, (payment_no,))
        je_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 1, '2211', 'ذمم موردين', 1000, 0)
        """, (je_id,))
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 2, '1211', 'النقدية', 0, 1000)
        """, (je_id,))
        
        # 2. الدفعة
        cur.execute("""
            INSERT INTO supplier_payments 
            (payment_no, reference_no, payment_date, supplier_id, payment_method, 
             amount, status, journal_entry_id, created_by)
            VALUES (?, ?, '2026-10-07', ?, 'CASH', 1000, 'POSTED', ?, 1)
        """, (payment_no, payment_no, supplier_id, je_id))
        sp_id = cur.lastrowid
        
        print(f"  ✅ دفعة: {payment_no} (id={sp_id}, je_id={je_id})")
    else:
        print(f"  ℹ️ الدفعة موجودة بالفعل")

# ============================================
# 5. إضافة تحصيل عميل
# ============================================
if customers:
    print("\n" + "=" * 60)
    print("💰 إضافة تحصيل عميل")
    print("=" * 60)
    
    customer_id = customers[0]['id']
    receipt_no = "RCP-TEST-001"
    
    cur.execute("SELECT id FROM customer_receipts WHERE receipt_no = ?", (receipt_no,))
    existing = cur.fetchone()
    
    if not existing:
        # 1. القيد
        cur.execute("""
            INSERT INTO journal_entries 
            (entry_no, entry_date, reference_type, reference_no, description, status, total_debit, total_credit)
            VALUES ('JE-TEST-002', '2026-10-07', 'CUSTOMER_RECEIPT', ?, 'تحصيل عميل اختبار', 'POSTED', 500, 500)
        """, (receipt_no,))
        je_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 1, '1211', 'النقدية', 500, 0)
        """, (je_id,))
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 2, '1221', 'ذمم عملاء', 0, 500)
        """, (je_id,))
        
        # 2. التحصيل
        cur.execute("""
            INSERT INTO customer_receipts 
            (receipt_no, reference_no, receipt_date, customer_id, receipt_method,
             amount, status, journal_entry_id, created_by)
            VALUES (?, ?, '2026-10-07', ?, 'CASH', 500, 'POSTED', ?, 1)
        """, (receipt_no, receipt_no, customer_id, je_id))
        cr_id = cur.lastrowid
        
        print(f"  ✅ تحصيل: {receipt_no} (id={cr_id}, je_id={je_id})")
    else:
        print(f"  ℹ️ التحصيل موجود بالفعل")

# ============================================
# 6. إضافة حركة خزينة
# ============================================
print("\n" + "=" * 60)
print("🔄 إضافة حركة خزينة")
print("=" * 60)

txn_ref = "TXN-TEST-001"
cur.execute("SELECT id FROM cash_box_transactions WHERE reference_no = ?", (txn_ref,))
existing = cur.fetchone()

if not existing:
    # 1. القيد
    cur.execute("""
        INSERT INTO journal_entries 
        (entry_no, entry_date, reference_type, reference_no, description, status, total_debit, total_credit)
        VALUES ('JE-TEST-003', '2026-10-07', 'CASH_BOX_TXN', ?, 'إيداع اختبار', 'POSTED', 2000, 2000)
    """, (txn_ref,))
    je_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO journal_entry_lines 
        (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
        VALUES (?, 1, '1211', 'النقدية', 2000, 0)
    """, (je_id,))
    cur.execute("""
        INSERT INTO journal_entry_lines 
        (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
        VALUES (?, 2, '3100', 'رأس المال', 0, 2000)
    """, (je_id,))
    
    # 2. الحركة
    cur.execute("""
        INSERT INTO cash_box_transactions 
        (box_id, box_type, txn_type, txn_date, amount, balance_after,
         reference_no, description, journal_entry_id, created_by)
        VALUES (?, 'CASH_BOX', 'DEPOSIT', '2026-10-07', 2000, 102000, ?, 'إيداع اختبار', ?, 1)
    """, (box_id, txn_ref, je_id))
    txn_id = cur.lastrowid
    
    print(f"  ✅ حركة: {txn_ref} (id={txn_id}, je_id={je_id})")
else:
    print(f"  ℹ️ الحركة موجودة بالفعل")

# ============================================
# 7. إضافة مصروف
# ============================================
print("\n" + "=" * 60)
print("🧾 إضافة مصروف")
print("=" * 60)

exp_no = "EXP-TEST-001"
cur.execute("SELECT id FROM petty_cash_expenses WHERE expense_no = ?", (exp_no,))
existing = cur.fetchone()

if not existing:
    # 1. القيد
    cur.execute("""
        INSERT INTO journal_entries 
        (entry_no, entry_date, reference_type, reference_no, description, status, total_debit, total_credit)
        VALUES ('JE-TEST-004', '2026-10-07', 'PETTY_CASH_EXPENSE', ?, 'مصروف اختبار', 'POSTED', 300, 300)
    """, (exp_no,))
    je_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO journal_entry_lines 
        (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
        VALUES (?, 1, '5299', 'مصروفات إدارية', 300, 0)
    """, (je_id,))
    cur.execute("""
        INSERT INTO journal_entry_lines 
        (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
        VALUES (?, 2, '1211', 'النقدية', 0, 300)
    """, (je_id,))
    
    # 2. المصروف
    cur.execute("""
        INSERT INTO petty_cash_expenses 
        (expense_no, reference_no, expense_date, category_id, amount,
         cash_box_id, description, status, journal_entry_id, created_by)
        VALUES (?, ?, '2026-10-07', ?, 300, ?, 'مصروف اختبار', 'POSTED', ?, 1)
    """, (exp_no, exp_no, cat_id, box_id, je_id))
    exp_id = cur.lastrowid
    
    print(f"  ✅ مصروف: {exp_no} (id={exp_id}, je_id={je_id})")
else:
    print(f"  ℹ️ المصروف موجود بالفعل")

conn.commit()

# ============================================
# 8. التحقق النهائي
# ============================================
print("\n" + "=" * 60)
print("📊 التحقق النهائي")
print("=" * 60)

for table, ref_field in [
    ('supplier_payments', 'payment_no'),
    ('customer_receipts', 'receipt_no'),
    ('cash_box_transactions', 'reference_no'),
    ('petty_cash_expenses', 'expense_no'),
]:
    cur.execute(f"SELECT COUNT(*) as total, SUM(CASE WHEN journal_entry_id IS NOT NULL THEN 1 ELSE 0 END) as linked FROM {table}")
    r = cur.fetchone()
    print(f"  {table}: {r['linked']}/{r['total']} مربوطة بقيد")

conn.close()

print("\n✅ تم إضافة البيانات التجريبية")