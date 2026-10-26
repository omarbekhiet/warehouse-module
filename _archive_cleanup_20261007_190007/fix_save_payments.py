"""
إضافة cash_box_id في save() + openAdd() في payments.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'payments.html')

print("=" * 60)
print("🔧 إصلاح save() + openAdd()")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. تعديل save() - إضافة جمع cashBoxVal + cash_box_id
# ============================================

# 1.1 إضافة جمع cashBoxVal في بداية save
old_save_start = """async function save() {
    const supplierId = document.getElementById('f-supplier').value;
    const method = document.getElementById('f-method').value;
    const amount = parseFloat(document.getElementById('f-amount').value);
    if (!supplierId) { alert('اختر المورد'); return; }
    if (!method) { alert('اختر طريقة السداد'); return; }
    if (!amount || amount <= 0) { alert('أدخل مبلغاً صحيحاً'); return; }"""

new_save_start = """async function save() {
    const supplierId = document.getElementById('f-supplier').value;
    const method = document.getElementById('f-method').value;
    const amount = parseFloat(document.getElementById('f-amount').value);
    if (!supplierId) { alert('اختر المورد'); return; }
    if (!method) { alert('اختر طريقة السداد'); return; }
    if (!amount || amount <= 0) { alert('أدخل مبلغاً صحيحاً'); return; }

    // ✅ استخرج cash_box_id
    const cashBoxVal = document.getElementById('f-cash-box') ? document.getElementById('f-cash-box').value : '';
    let cashBoxId = null, cashBoxType = 'CASH_BOX';
    if (cashBoxVal) {
        const parts = cashBoxVal.split('|');
        cashBoxType = parts[0];
        cashBoxId = parseInt(parts[1]);
    }"""

if 'cashBoxVal' not in content:
    if old_save_start in content:
        content = content.replace(old_save_start, new_save_start)
        print("  ✅ تم إضافة جمع cashBoxVal في save()")
    else:
        print("  ⚠️ نمط بداية save() مش موجود")
else:
    print("  ℹ️ cashBoxVal موجود بالفعل")

# 1.2 إضافة cash_box_id في data
old_data = """    const data = {
        payment_date: document.getElementById('f-date').value,
        supplier_id: parseInt(supplierId),
        payment_method: method,
        amount: amount,
        reference: document.getElementById('f-reference').value,
        notes: document.getElementById('f-notes').value,
        allocations: allocations,"""

new_data = """    const data = {
        payment_date: document.getElementById('f-date').value,
        supplier_id: parseInt(supplierId),
        payment_method: method,
        amount: amount,
        reference: document.getElementById('f-reference').value,
        notes: document.getElementById('f-notes').value,
        cash_box_id: cashBoxId,
        cash_box_type: cashBoxType,
        allocations: allocations,"""

if 'cash_box_id: cashBoxId' not in content:
    if old_data in content:
        content = content.replace(old_data, new_data)
        print("  ✅ تم إضافة cash_box_id في data")
    else:
        print("  ⚠️ نمط data مش موجود")
else:
    print("  ℹ️ cash_box_id في data موجود")

# ============================================
# 2. تعديل openAdd() - تصفير الخزينة
# ============================================

old_openadd = """    document.getElementById('f-method').value = 'CASH';
    document.getElementById('f-amount').value = '';"""

new_openadd = """    document.getElementById('f-method').value = 'CASH';
    const cbEl = document.getElementById('f-cash-box');
    if (cbEl) cbEl.value = '';
    document.getElementById('f-amount').value = '';"""

if "cbEl.value = ''" not in content:
    if old_openadd in content:
        content = content.replace(old_openadd, new_openadd)
        print("  ✅ تم إضافة تصفير الخزينة في openAdd()")
    else:
        print("  ⚠️ نمط openAdd() مش موجود")
else:
    print("  ℹ️ تصفير الخزينة موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
print(f"  cashBoxVal: {'✅' if 'cashBoxVal' in content else '❌'}")
print(f"  cash_box_id في data: {'✅' if 'cash_box_id: cashBoxId' in content else '❌'}")
print(f"  تصفير الخزينة: {'✅' if 'cbEl.value' in content else '❌'}")