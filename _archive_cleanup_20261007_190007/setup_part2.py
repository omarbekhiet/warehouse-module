"""
الجزء 2: إضافة cash_box للتحصيل + تحديث index.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================
# 1. إضافة cash_box للتحصيل
# ============================================
print("📝 1. تحديث payment_service.py (التحصيل)...")

path = os.path.join(BASE, 'app', 'services', 'payment_service.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# النمط الفعلي
old = """            receipt_id = cur.lastrowid

            # 4. القيد (فحص auto_journal_receipts)"""

new = """            receipt_id = cur.lastrowid
            
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

if old in content:
    content = content.replace(old, new)
    print("  ✅ تم إضافة cash_box للتحصيل")
else:
    print("  ⚠️ النمط مش موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 2. تحديث index.html - إضافة روابط
# ============================================
print("\n🎨 2. تحديث index.html...")

index_path = os.path.join(BASE, 'app', 'static', 'index.html')

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن نمط قسم المحاسبة
# نبحث عن آخر رابط في قسم المحاسبة
old_patterns = [
    # نمط 1
    """{file: 'clearing.html', name: 'الحسابات الوسيطة'}, {file: 'financial_reports.html', name: 'التقارير المالية'},
        {file: 'cash_boxes.html', name: 'الخزائن والبنوك'}, {file: 'expenses.html', name: 'صرف النثريات'}""",
    # نمط 2
    """{file: 'cash_boxes.html', name: 'الخزائن والبنوك'}, {file: 'expenses.html', name: 'صرف النثريات'}""",
]

new_links = """{file: 'cash_boxes.html', name: 'الخزائن والبنوك'}, {file: 'expenses.html', name: 'صرف النثريات'},
        {file: 'cash_box_transactions.html', name: 'حركات الخزائن'}, {file: 'expense_categories.html', name: 'تصنيفات المصروفات'},
        {file: 'bank_reconciliation.html', name: 'التسوية البنكية'}, {file: 'cash_box_reports.html', name: 'تقارير الخزائن'}"""

updated = False
for old in old_patterns:
    if old in content and 'bank_reconciliation.html' not in content:
        content = content.replace(old, new_links)
        updated = True
        print("  ✅ تم إضافة الروابط في SCREENS")
        break

if not updated:
    if 'bank_reconciliation.html' in content:
        print("  ℹ️ الروابط موجودة بالفعل")
    else:
        print("  ⚠️ ما لقيتش النمط — ابعتلي السطور")

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# 3. تحديث payments.html - إضافة حقل الخزينة
# ============================================
print("\n💳 3. تحديث payments.html...")

pay_path = os.path.join(BASE, 'app', 'static', 'payments.html')

with open(pay_path, 'r', encoding='utf-8') as f:
    content = f.read()

# إضافة حقل cash-box بعد طريقة السداد
if 'f-cash-box' not in content:
    old_field = """        <div class="col-md-4">
            <label class="form-label">طريقة السداد *</label>
            <select class="form-select" id="f-method" onchange="onMethodChange()"></select>
        </div>"""
    
    new_field = """        <div class="col-md-4">
            <label class="form-label">طريقة السداد *</label>
            <select class="form-select" id="f-method" onchange="onMethodChange()"></select>
        </div>
        <div class="col-md-4">
            <label class="form-label">الخزينة/البنك</label>
            <select class="form-select" id="f-cash-box">
                <option value="">— بدون —</option>
            </select>
        </div>"""
    
    if old_field in content:
        content = content.replace(old_field, new_field)
        print("  ✅ تم إضافة حقل الخزينة")
    else:
        print("  ⚠️ نمط طريقة السداد مش موجود")

# إضافة boxesList و fetch
if 'boxesList' not in content:
    # ضيف بعد methodsList
    content = content.replace(
        'let methodsList = [];',
        'let methodsList = [];\nlet boxesList = [];'
    )
    print("  ✅ تم إضافة boxesList")

# تحديث loadRefs
old_loadrefs = """async function loadRefs() {
    const [s, m] = await Promise.all([
        fetch(`${API}/suppliers/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/payments/methods/`).then(r => r.json()).catch(() => ({data: []}))
    ]);
    suppliersList = s.data || [];
    methodsList = m.data || [];"""

new_loadrefs = """async function loadRefs() {
    const [s, m, b] = await Promise.all([
        fetch(`${API}/suppliers/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/payments/methods/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/cash-boxes/all-active/`).then(r => r.json()).catch(() => ({data: []}))
    ]);
    suppliersList = s.data || [];
    methodsList = m.data || [];
    boxesList = b.data || [];
    
    const boxSelect = document.getElementById('f-cash-box');
    if (boxSelect) {
        boxSelect.innerHTML = '<option value="">— بدون —</option>' +
            boxesList.map(b => `<option value="${b.box_type}|${b.id}">[${b.box_type === 'CASH_BOX' ? 'خزينة' : b.box_type === 'BANK' ? 'بنك' : 'بطاقة'}] ${b.code} - ${b.name} (${b.balance.toFixed(2)})</option>`).join('');
    }"""

if old_loadrefs in content:
    content = content.replace(old_loadrefs, new_loadrefs)
    print("  ✅ تم تحديث loadRefs")

with open(pay_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# ملخص
# ============================================
print("\n" + "=" * 60)
print("✅ تم!")
print("=" * 60)