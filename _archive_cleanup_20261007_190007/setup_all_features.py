"""
سكريبت شامل:
1. ربط الخزائن بالدفع/التحصيل
2. إنشاء جداول التسوية البنكية
3. APIs التقارير
4. دعم الفروع
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'warehouse.db')

print("=" * 60)
print("🚀 إعداد كل الميزات")
print("=" * 60)

# ============================================
# 1. تحديث payment_service.py
# ============================================
print("\n📝 1. تحديث payment_service.py...")

payment_service_path = os.path.join(BASE, 'app', 'services', 'payment_service.py')

with open(payment_service_path, 'r', encoding='utf-8') as f:
    content = f.read()

# إضافة cash_box للـ supplier payment
if 'cash_box_id' not in content:
    old1 = """            payment_id = cur.lastrowid
            
            # فحص القيد التلقائي"""
    new1 = """            payment_id = cur.lastrowid
            
            # ✅ تسجيل حركة الخزينة (دفع)
            cash_box_id = data.get('cash_box_id')
            cash_box_type = data.get('cash_box_type', 'CASH_BOX')
            
            if cash_box_id:
                table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
                box_table = table_map.get(cash_box_type, 'cash_boxes')
                
                cur.execute(f"SELECT * FROM {box_table} WHERE id=?", (cash_box_id,))
                box = cur.fetchone()
                
                if box:
                    current_bal = float(box['current_balance'] or 0)
                    new_bal = current_bal - float(data['amount'])
                    
                    cur.execute(f"UPDATE {box_table} SET current_balance=? WHERE id=?", (new_bal, cash_box_id))
                    
                    cur.execute(\"\"\"
                        INSERT INTO cash_box_transactions 
                        (box_id, box_type, txn_type, txn_date, amount, balance_after,
                         reference_no, description, created_by)
                        VALUES (?, ?, 'WITHDRAW', ?, ?, ?, ?, ?, ?)
                    \"\"\", (
                        cash_box_id, cash_box_type, data['payment_date'],
                        float(data['amount']), new_bal, payment_no,
                        f"دفعة لمورد - {payment_no}", user_id
                    ))
            
            # فحص القيد التلقائي"""
    
    if old1 in content:
        content = content.replace(old1, new1)
        print("  ✅ تم إضافة cash_box للدفع")
    else:
        print("  ⚠️ نمط الدفع مش موجود")

# إضافة cash_box للـ customer receipt
if content.count('cash_box_id') < 2:
    old2 = """            receipt_id = cur.lastrowid
            
            # 4. القيد"""
    new2 = """            receipt_id = cur.lastrowid
            
            # ✅ تسجيل حركة الخزينة (تحصيل)
            cash_box_id = data.get('cash_box_id')
            cash_box_type = data.get('cash_box_type', 'CASH_BOX')
            
            if cash_box_id:
                table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
                box_table = table_map.get(cash_box_type, 'cash_boxes')
                
                cur.execute(f"SELECT * FROM {box_table} WHERE id=?", (cash_box_id,))
                box = cur.fetchone()
                
                if box:
                    current_bal = float(box['current_balance'] or 0)
                    new_bal = current_bal + float(data['amount'])
                    
                    cur.execute(f"UPDATE {box_table} SET current_balance=? WHERE id=?", (new_bal, cash_box_id))
                    
                    cur.execute(\"\"\"
                        INSERT INTO cash_box_transactions 
                        (box_id, box_type, txn_type, txn_date, amount, balance_after,
                         reference_no, description, created_by)
                        VALUES (?, ?, 'DEPOSIT', ?, ?, ?, ?, ?, ?)
                    \"\"\", (
                        cash_box_id, cash_box_type, data['receipt_date'],
                        float(data['amount']), new_bal, receipt_no,
                        f"تحصيل من عميل - {receipt_no}", user_id
                    ))
            
            # 4. القيد"""
    
    if old2 in content:
        content = content.replace(old2, new2)
        print("  ✅ تم إضافة cash_box للتحصيل")
    else:
        print("  ⚠️ نمط التحصيل مش موجود")

with open(payment_service_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 2. إنشاء جداول التسوية البنكية والفروع
# ============================================
print("\n📊 2. إنشاء جداول التسوية والفروع...")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Bank Reconciliations
cur.execute("""
    CREATE TABLE IF NOT EXISTS bank_reconciliations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_id INTEGER NOT NULL,
        reconciliation_date TEXT NOT NULL,
        statement_balance REAL NOT NULL,
        system_balance REAL DEFAULT 0,
        difference REAL DEFAULT 0,
        status TEXT DEFAULT 'DRAFT',
        notes TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bank_id) REFERENCES banks(id)
    )
""")
print("  ✅ bank_reconciliations")

# Bank Reconciliation Items
cur.execute("""
    CREATE TABLE IF NOT EXISTS bank_reconciliation_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reconciliation_id INTEGER NOT NULL,
        txn_type TEXT,
        reference_no TEXT,
        txn_date TEXT,
        amount REAL,
        is_matched INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (reconciliation_id) REFERENCES bank_reconciliations(id) ON DELETE CASCADE
    )
""")
print("  ✅ bank_reconciliation_items")

# Branches (فروع)
cur.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        name_en TEXT,
        address TEXT,
        phone TEXT,
        manager_name TEXT,
        is_active INTEGER DEFAULT 1,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ branches")

# فهارس
cur.execute("CREATE INDEX IF NOT EXISTS idx_recon_bank ON bank_reconciliations(bank_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_recon_date ON bank_reconciliations(reconciliation_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_recon_items ON bank_reconciliation_items(reconciliation_id)")

conn.commit()
conn.close()

# ============================================
# 3. تحديث index.html
# ============================================
print("\n🎨 3. تحديث index.html...")

index_path = os.path.join(BASE, 'app', 'static', 'index.html')

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# إضافة روابط جديدة في قسم المحاسبة
if 'bank_reconciliation.html' not in content:
    old_link = """{file: 'cash_boxes.html', name: 'الخزائن والبنوك'}, {file: 'expenses.html', name: 'صرف النثريات'}"""
    new_link = """{file: 'cash_boxes.html', name: 'الخزائن والبنوك'}, {file: 'expenses.html', name: 'صرف النثريات'},
        {file: 'bank_reconciliation.html', name: 'التسوية البنكية'}, {file: 'cash_box_reports.html', name: 'تقارير الخزائن'}"""
    if old_link in content:
        content = content.replace(old_link, new_link)
        print("  ✅ تم تحديث SCREENS")

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 4. تحديث permissions.js
# ============================================
print("\n🔐 4. تحديث permissions.js...")

perms_path = os.path.join(BASE, 'app', 'static', 'permissions.js')

with open(perms_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'bank_reconciliation.html' not in content:
    old = "'cash_boxes.html', 'expenses.html'"
    new = "'cash_boxes.html', 'expenses.html', 'bank_reconciliation.html', 'cash_box_reports.html', 'branches.html'"
    content = content.replace(old, new)
    print("  ✅ تم تحديث ACCOUNTANT")

with open(perms_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# ملخص
# ============================================
print("\n" + "=" * 60)
print("✅ تم إعداد كل الميزات!")
print("=" * 60)
print("\n📋 الخطوات التالية:")
print("  1. إنشاء ملفات الشاشات (bank_reconciliation.html, cash_box_reports.html, branches.html)")
print("  2. إضافة APIs للتسوية والتقارير")
print("  3. إعادة تشغيل السيرفر")
print("\n⚠️ الـ APIs والشاشات هتيجي في الأجزاء الجاية.")