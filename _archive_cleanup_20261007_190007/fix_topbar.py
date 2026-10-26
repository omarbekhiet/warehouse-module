"""
تصغير الشريط العلوي في accounts.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'accounts.html')

print("=" * 60)
print("🎨 تصغير الشريط العلوي")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. تصغير padding الصفحة الرئيسية
old_container = '<div class="col-md-10 p-4">'
new_container = '<div class="col-md-10 p-2">'
if old_container in content:
    content = content.replace(old_container, new_container, 1)
    print("  ✅ تم تصغير padding الصفحة (p-4 → p-2)")

# 2. تصغير الـ Header
old_header = '''<div class="d-flex justify-content-between mb-4">
<h2><i class="bi bi-book"></i> الدليل المحاسبي</h2>
<a href="index.html" class="btn btn-outline-secondary">
    <i class="bi bi-house-fill"></i> الرئيسية
</a>
<div>
<button class="btn btn-outline-secondary" onclick="load()"><i class="bi bi-arrow-clockwise"></i> تحديث</button>
<button class="btn btn-primary" onclick="openAdd()"><i class="bi bi-plus-circle"></i> حساب جديد</button>
</div>
</div>'''

new_header = '''<div class="d-flex justify-content-between align-items-center mb-2">
<h5 class="mb-0"><i class="bi bi-book"></i> الدليل المحاسبي</h5>
<div class="d-flex gap-1">
<a href="index.html" class="btn btn-sm btn-outline-secondary">
    <i class="bi bi-house-fill"></i> الرئيسية
</a>
<button class="btn btn-sm btn-outline-secondary" onclick="load()"><i class="bi bi-arrow-clockwise"></i></button>
<button class="btn btn-sm btn-primary" onclick="openAdd()"><i class="bi bi-plus-circle"></i> حساب جديد</button>
</div>
</div>'''

if old_header in content:
    content = content.replace(old_header, new_header, 1)
    print("  ✅ تم تصغير الـ Header")

# 3. تصغير الإحصائيات (أصغر + مسافات أقل)
old_stats = '''<div class="row g-2 mb-2">
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">الإجمالي</div><div class="value text-primary" id="s-total" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">قابلة للترحيل</div><div class="value text-success" id="s-leaf" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">تجميعية</div><div class="value text-warning" id="s-group" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">أنواع الحسابات</div><div class="value text-info" id="s-types" style="font-size:1.1rem;">-</div></div></div>
</div>'''

new_stats = '''<div class="row g-1 mb-2">
<div class="col-3"><div class="card p-1 text-center"><small class="text-muted" style="font-size:0.68rem;">الإجمالي</small><div class="text-primary fw-bold" id="s-total" style="font-size:0.95rem;">-</div></div></div>
<div class="col-3"><div class="card p-1 text-center"><small class="text-muted" style="font-size:0.68rem;">للترحيل</small><div class="text-success fw-bold" id="s-leaf" style="font-size:0.95rem;">-</div></div></div>
<div class="col-3"><div class="card p-1 text-center"><small class="text-muted" style="font-size:0.68rem;">تجميعية</small><div class="text-warning fw-bold" id="s-group" style="font-size:0.95rem;">-</div></div></div>
<div class="col-3"><div class="card p-1 text-center"><small class="text-muted" style="font-size:0.68rem;">أنواع</small><div class="text-info fw-bold" id="s-types" style="font-size:0.95rem;">-</div></div></div>
</div>'''

if old_stats in content:
    content = content.replace(old_stats, new_stats, 1)
    print("  ✅ تم تصغير الإحصائيات")

# 4. تصغير الفلاتر
old_filters = '''<div class="card p-2 mb-2">
<div class="row g-2 align-items-center">
<div class="col-md-4"><input class="form-control form-control-sm" id="flt-search" placeholder="🔍 ابحث بالكود أو الاسم..." oninput="filterTree()"></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-level" onchange="filterTree()">
<option value="">كل المستويات</option>
<option value="L1">L1</option>
<option value="L2">L2</option>
<option value="L3">L3</option>
<option value="L4">L4</option>
</select></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-nature" onchange="filterTree()">
<option value="">كل الطبائع</option>
<option value="D">مدين</option>
<option value="C">دائن</option>
<option value="CC">مقابل</option>
</select></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-stmt" onchange="filterTree()">
<option value="">كل القوائم</option>
<option value="BS">ميزانية</option>
<option value="IS">دخل</option>
<option value="EQ">حقوق ملكية</option>
</select></div>
<div class="col-md-2"><button class="btn btn-outline-secondary btn-sm w-100" onclick="resetFilters()"><i class="bi bi-x-circle"></i> مسح</button></div>
</div>
</div>'''

new_filters = '''<div class="card p-1 mb-2">
<div class="row g-1 align-items-center">
<div class="col-md-4"><input class="form-control form-control-sm" id="flt-search" placeholder="🔍 ابحث..." oninput="filterTree()" style="font-size:0.78rem;padding:3px 8px;"></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-level" onchange="filterTree()" style="font-size:0.78rem;padding:3px 8px;">
<option value="">كل المستويات</option>
<option value="L1">L1</option>
<option value="L2">L2</option>
<option value="L3">L3</option>
<option value="L4">L4</option>
</select></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-nature" onchange="filterTree()" style="font-size:0.78rem;padding:3px 8px;">
<option value="">كل الطبائع</option>
<option value="D">مدين</option>
<option value="C">دائن</option>
<option value="CC">مقابل</option>
</select></div>
<div class="col-md-2">
<select class="form-select form-select-sm" id="flt-stmt" onchange="filterTree()" style="font-size:0.78rem;padding:3px 8px;">
<option value="">كل القوائم</option>
<option value="BS">ميزانية</option>
<option value="IS">دخل</option>
<option value="EQ">حقوق ملكية</option>
</select></div>
<div class="col-md-2"><button class="btn btn-outline-secondary btn-sm w-100" onclick="resetFilters()" style="font-size:0.78rem;padding:3px 8px;"><i class="bi bi-x-circle"></i> مسح</button></div>
</div>
</div>'''

if old_filters in content:
    content = content.replace(old_filters, new_filters, 1)
    print("  ✅ تم تصغير الفلاتر")

# 5. تصغير الـ tree-container
old_tree = '''<div class="card p-3">
<div class="tree-container">'''
new_tree = '''<div class="card p-1">
<div class="tree-container" style="max-height: calc(100vh - 240px);">'''
if old_tree in content:
    content = content.replace(old_tree, new_tree, 1)
    print("  ✅ تم تصغير الجدول + زيادة ارتفاعه")

# 6. تصغير الحواف العامة
old_body = 'body { font-family:'
new_body = 'body { padding: 0 !important; font-family:'
# مش هنعدل body — هنعدل .container-fluid
old_cf = '.container-fluid'
# نضيف CSS جديد في النهاية
extra_css = '''
/* === تصغير إضافي === */
.container-fluid { padding: 0 !important; }
.col-md-10.p-2 { padding: 8px !important; }
.card { margin-bottom: 6px !important; }
h5 { font-size: 1.1rem !important; }
.btn-sm { padding: 2px 8px !important; font-size: 0.75rem !important; }
.tree-table thead th { padding: 6px 6px !important; font-size: 0.72rem !important; }
.tree-table td { padding: 5px 6px !important; font-size: 0.78rem !important; }
.tree-table { font-size: 0.78rem !important; }
.col-code { width: 70px !important; }
.col-level { width: 55px !important; }
.col-actions { width: 100px !important; }
.btn-action { padding: 2px 5px !important; font-size: 0.68rem !important; }
.badge { padding: 2px 6px !important; font-size: 0.65rem !important; }
'''

# ضيف CSS في نهاية الـ <style>
if '/* === تصغير إضافي === */' not in content:
    idx = content.rfind('</style>')
    if idx > 0:
        content = content[:idx] + extra_css + '\n' + content[idx:]
        print("  ✅ تم إضافة CSS إضافي")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ تم التعديل!")