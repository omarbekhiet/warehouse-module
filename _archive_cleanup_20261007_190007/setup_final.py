"""
الجزء النهائي: إضافة cash_box للدفع والتحصيل + تحديث payments.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================
# 1. payment_service.py - إضافة cash_box
# ============================================
print("=" * 60)
print("📝 1. تحديث payment_service.py")
print("=" * 60)

path = os.path.join(BASE, 'app', 'services', 'payment_service.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# عدّاد للتعديلات
changes = 0

# ---- أ) إضافة للتحصيل (بعد receipt_id) ----
if "cash_box_id = data.get('cash_box_id')" not in content or content.count("cash_box_id = data.get('cash_box_id')") < 2:
    old1 = """            receipt_id = cur.lastrowid

            # 4. القيد (فحص auto_journal_receipts)"""
    
    new1 = """            receipt_id = cur.lastrowid
            
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

            # 4. القيد (فحص auto_journal_receipts)"""
    
    if old1 in content:
        content = content.replace(old1, new1)
        print("  ✅ تم إضافة cash_box للتحصيل")
        changes += 1
    else:
        print("  ⚠️ نمط التحصيل مش موجود — ممكن يكون اتضاف")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 2. payments.html - إضافة حقل الخزينة
# ============================================
print("\n" + "=" * 60)
print("💳 2. تحديث payments.html")
print("=" * 60)

pay_path = os.path.join(BASE, 'app', 'static', 'payments.html')

with open(pay_path, 'r', encoding='utf-8') as f:
    content = f.read()

# النمط الفعلي (سطر 66-68) - كله في سطر واحد
old_field = """        <div class="col-md-4"><label class="form-label">التاريخ *</label><input type="date" class="form-control" id="f-date"></div>
        <div class="col-md-4"><label class="form-label">المورد *</label><select class="form-select" id="f-supplier" onchange="onSupplierChange()"></select></div>
        <div class="col-md-4"><label class="form-label">طريقة السداد *</label><select class="form-select" id="f-method" onchange="onMethodChange()"></select></div>
    </div>"""

new_field = """        <div class="col-md-4"><label class="form-label">التاريخ *</label><input type="date" class="form-control" id="f-date"></div>
        <div class="col-md-4"><label class="form-label">المورد *</label><select class="form-select" id="f-supplier" onchange="onSupplierChange()"></select></div>
        <div class="col-md-4"><label class="form-label">طريقة السداد *</label><select class="form-select" id="f-method" onchange="onMethodChange()"></select></div>
        <div class="col-md-4"><label class="form-label">الخزينة/البنك</label><select class="form-select" id="f-cash-box"><option value="">— بدون —</option></select></div>
    </div>"""

if 'f-cash-box' not in content:
    if old_field in content:
        content = content.replace(old_field, new_field)
        print("  ✅ تم إضافة حقل الخزينة")
    else:
        print("  ⚠️ نمط الحقول مش موجود")
else:
    print("  ℹ️ حقل الخزينة موجود بالفعل")

with open(pay_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 3. التحقق
# ============================================
print("\n" + "=" * 60)
print("✅ التحقق")
print("=" * 60)

with open(pay_path, 'r', encoding='utf-8') as f:
    content = f.read()
    print(f"  f-cash-box في payments.html: {'✅' if 'f-cash-box' in content else '❌'}")
    print(f"  boxesList في payments.html: {'✅' if 'boxesList' in content else '❌'}")

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
    count = content.count("cash_box_id = data.get('cash_box_id')")
    print(f"  cash_box في payment_service.py: {'✅' if count >= 2 else '⚠️ (' + str(count) + ')'}")

print("\n" + "=" * 60)
print("✅ تم!")
print("=" * 60)