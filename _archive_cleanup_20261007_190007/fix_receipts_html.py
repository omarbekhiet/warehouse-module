"""
إضافة cash_box في customer_receipts.html
- حقل HTML
- جلب الخزائن (boxesList + fetch)
- save() يبعت cash_box_id
- openAdd() يصفّر الخزينة
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'customer_receipts.html')

print("=" * 60)
print("🔧 إصلاح customer_receipts.html")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. إضافة حقل الخزينة في HTML
# ============================================
print("\n📝 1. حقل الخزينة في HTML...")

# السطر 139: طريقة التحصيل
old_html = '''            <select class="form-select" id="f-method" onchange="onMethodChange()"></select>
        </div>'''

new_html = '''            <select class="form-select" id="f-method" onchange="onMethodChange()"></select>
        </div>
        <div class="col-md-4">
            <label class="form-label">الخزينة/البنك</label>
            <select class="form-select" id="f-cash-box"><option value="">— بدون —</option></select>
        </div>'''

if '<select class="form-select" id="f-cash-box"' in content:
    print("  ℹ️ الحقل موجود بالفعل")
elif old_html in content:
    content = content.replace(old_html, new_html, 1)
    print("  ✅ تم إضافة حقل الخزينة")
else:
    print("  ⚠️ السطر المميز مش موجود")

# ============================================
# 2. إضافة boxesList في JavaScript
# ============================================
print("\n📝 2. boxesList في JavaScript...")

if 'let boxesList' not in content:
    # ابحث عن let customersList
    if 'let customersList = [];' in content:
        content = content.replace(
            'let customersList = [];',
            'let customersList = [];\nlet boxesList = [];',
            1
        )
        print("  ✅ تم إضافة boxesList")
    else:
        print("  ⚠️ ما لقيتش customersList")
else:
    print("  ℹ️ boxesList موجود")

# ============================================
# 3. تحديث loadRefs لجلب الخزائن
# ============================================
print("\n📝 3. loadRefs...")

# ابحث عن loadRefs
old_loadrefs = '''async function loadRefs() {
    const [c, m] = await Promise.all([
        fetch(`${API}/customers/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/payments/methods/`).then(r => r.json()).catch(() => ({data: []}))
    ]);'''

new_loadrefs = '''async function loadRefs() {
    const [c, m, b] = await Promise.all([
        fetch(`${API}/customers/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/payments/methods/`).then(r => r.json()).catch(() => ({data: []})),
        fetch(`${API}/cash-boxes/all-active/`).then(r => r.json()).catch(() => ({data: []}))
    ]);'''

if 'cash-boxes/all-active' not in content:
    if old_loadrefs in content:
        content = content.replace(old_loadrefs, new_loadrefs)
        print("  ✅ تم إضافة fetch للخزائن")
    else:
        print("  ⚠️ نمط loadRefs مش موجود")
else:
    print("  ℹ️ fetch موجود")

# إضافة boxesList = b.data
if 'boxesList = b.data' not in content:
    # ابحث عن methodsList = m.data
    if 'methodsList = m.data || [];' in content:
        content = content.replace(
            'methodsList = m.data || [];',
            '''methodsList = m.data || [];
    boxesList = b.data || [];
    
    // املأ قائمة الخزائن
    const boxSel = document.getElementById('f-cash-box');
    if (boxSel) {
        boxSel.innerHTML = '<option value="">— بدون —</option>' +
            boxesList.map(b => `<option value="${b.box_type}|${b.id}">[${b.box_type === 'CASH_BOX' ? 'خزينة' : b.box_type === 'BANK' ? 'بنك' : 'بطاقة'}] ${b.code} - ${b.name} (${b.balance.toFixed(2)})</option>`).join('');
    }''',
            1
        )
        print("  ✅ تم إضافة تعبئة قائمة الخزائن")
    else:
        print("  ⚠️ ما لقيتش methodsList = m.data")

# ============================================
# 4. تحديث save() - إضافة cash_box_id
# ============================================
print("\n📝 4. save()...")

# إضافة جمع cashBoxVal
old_save = '''async function save() {
    const customerId = document.getElementById('f-customer').value;
    const method = document.getElementById('f-method').value;
    const amount = parseFloat(document.getElementById('f-amount').value);

    if (!customerId) { alert('اختر العميل'); return; }
    if (!method) { alert('اختر طريقة التحصيل'); return; }
    if (!amount || amount <= 0) { alert('أدخل مبلغاً صحيحاً'); return; }'''

new_save = '''async function save() {
    const customerId = document.getElementById('f-customer').value;
    const method = document.getElementById('f-method').value;
    const amount = parseFloat(document.getElementById('f-amount').value);

    if (!customerId) { alert('اختر العميل'); return; }
    if (!method) { alert('اختر طريقة التحصيل'); return; }
    if (!amount || amount <= 0) { alert('أدخل مبلغاً صحيحاً'); return; }

    // ✅ استخرج cash_box_id
    const cashBoxVal = document.getElementById('f-cash-box') ? document.getElementById('f-cash-box').value : '';
    let cashBoxId = null, cashBoxType = 'CASH_BOX';
    if (cashBoxVal) {
        const parts = cashBoxVal.split('|');
        cashBoxType = parts[0];
        cashBoxId = parseInt(parts[1]);
    }'''

if 'cashBoxVal' not in content:
    if old_save in content:
        content = content.replace(old_save, new_save)
        print("  ✅ تم إضافة جمع cashBoxVal")
    else:
        print("  ⚠️ نمط save() مش موجود")
else:
    print("  ℹ️ cashBoxVal موجود")

# إضافة cash_box_id في data
if 'cash_box_id: cashBoxId' not in content:
    # ابحث عن allocations: allocations
    if 'allocations: allocations' in content:
        content = content.replace(
            'allocations: allocations',
            'cash_box_id: cashBoxId,\n        cash_box_type: cashBoxType,\n        allocations: allocations',
            1
        )
        print("  ✅ تم إضافة cash_box_id في data")
    else:
        print("  ⚠️ ما لقيتش allocations: allocations")

# ============================================
# 5. تحديث openAdd() - تصفير الخزينة
# ============================================
print("\n📝 5. openAdd()...")

old_openadd = '''    document.getElementById('f-method').value = 'CASH';
    document.getElementById('f-amount').value = '';'''

new_openadd = '''    document.getElementById('f-method').value = 'CASH';
    const cbEl = document.getElementById('f-cash-box');
    if (cbEl) cbEl.value = '';
    document.getElementById('f-amount').value = '';'''

if "cbEl.value = ''" not in content:
    if old_openadd in content:
        content = content.replace(old_openadd, new_openadd)
        print("  ✅ تم إضافة تصفير الخزينة")
    else:
        print("  ⚠️ نمط openAdd() مش موجود")
else:
    print("  ℹ️ تصفير الخزينة موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n" + "=" * 60)
print("📊 التحقق:")
print("=" * 60)
print(f"  حقل HTML: {'✅' if '<select class=\"form-select\" id=\"f-cash-box\"' in content else '❌'}")
print(f"  boxesList: {'✅' if 'let boxesList' in content else '❌'}")
print(f"  fetch الخزائن: {'✅' if 'cash-boxes/all-active' in content else '❌'}")
print(f"  cashBoxVal: {'✅' if 'cashBoxVal' in content else '❌'}")
print(f"  cash_box_id في data: {'✅' if 'cash_box_id: cashBoxId' in content else '❌'}")
print(f"  تصفير في openAdd: {'✅' if 'cbEl.value' in content else '❌'}")