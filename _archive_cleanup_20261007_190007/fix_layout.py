"""
تعديل layout accounts.html — تصغير الإحصائيات والفلاتر
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'accounts.html')

print("=" * 60)
print("🎨 تعديل Layout")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. تصغير الإحصائيات
old_stats = '''<div class="row g-3 mb-3">
<div class="col-md-3"><div class="stat-card card p-3"><div class="label">إجمالي الحسابات</div><div class="value text-primary" id="s-total">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-3"><div class="label">قابلة للترحيل</div><div class="value text-success" id="s-leaf">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-3"><div class="label">تجميعية</div><div class="value text-warning" id="s-group">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-3"><div class="label">أنواع الحسابات</div><div class="value text-info" id="s-types">-</div></div></div>
</div>'''

new_stats = '''<div class="row g-2 mb-2">
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">الإجمالي</div><div class="value text-primary" id="s-total" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">قابلة للترحيل</div><div class="value text-success" id="s-leaf" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">تجميعية</div><div class="value text-warning" id="s-group" style="font-size:1.1rem;">-</div></div></div>
<div class="col-md-3"><div class="stat-card card p-2 text-center"><div class="label" style="font-size:0.7rem;">أنواع الحسابات</div><div class="value text-info" id="s-types" style="font-size:1.1rem;">-</div></div></div>
</div>'''

if old_stats in content:
    content = content.replace(old_stats, new_stats, 1)
    print("  ✅ تم تصغير الإحصائيات")

# 2. تصغير الفلاتر
old_filters = '''<div class="card p-3 mb-3">
<div class="row g-2">
<div class="col-md-3"><input class="form-control" id="flt-search" placeholder="ابحث بالكود أو الاسم..." oninput="filterTree()"></div>
<div class="col-md-2">
<select class="form-select" id="flt-level" onchange="filterTree()">
<option value="">كل المستويات</option>
<option value="L1">L1 - رئيسي</option>
<option value="L2">L2 - فئة</option>
<option value="L3">L3 - مجموعة</option>
<option value="L4">L4 - حساب</option>
</select></div>
<div class="col-md-2">
<select class="form-select" id="flt-nature" onchange="filterTree()">
<option value="">كل الطبائع</option>
<option value="D">مدين (D)</option>
<option value="C">دائن (C)</option>
<option value="CC">دائن مقابل (CC)</option>
</select></div>
<div class="col-md-2">
<select class="form-select" id="flt-stmt" onchange="filterTree()">
<option value="">كل القوائم</option>
<option value="BS">الميزانية (BS)</option>
<option value="IS">الدخل (IS)</option>
<option value="EQ">حقوق الملكية (EQ)</option>
</select></div>
<div class="col-md-3"><button class="btn btn-outline-secondary w-100" onclick="resetFilters()"><i class="bi bi-x-circle"></i> مسح الفلاتر</button></div>
</div>
</div>'''

new_filters = '''<div class="card p-2 mb-2">
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

if old_filters in content:
    content = content.replace(old_filters, new_filters, 1)
    print("  ✅ تم تصغير الفلاتر")

# 3. شيل الـ Legend (دليل الألوان) عشان يوفر مساحة
old_legend_start = '<div class="tree-legend">'
old_legend_end = '</div>'
idx_start = content.find(old_legend_start)
if idx_start > 0:
    # ابحث عن آخر </div> بعدها
    idx_end = content.find('</div>\n\n<!-- Tree in columns -->', idx_start)
    if idx_end < 0:
        idx_end = content.find('<!-- Tree in columns -->', idx_start)
        if idx_end > 0:
            idx_end = content.rfind('</div>', idx_start, idx_end) + 6
    
    if idx_end > idx_start:
        # شيل الـ Legend
        content = content[:idx_start] + content[idx_end:]
        print("  ✅ تم شيل دليل الألوان")

# 4. اضبط tree-container
old_container = '.tree-container {\n    max-height: 600px;'
new_container = '.tree-container {\n    max-height: calc(100vh - 350px);'
if old_container in content:
    content = content.replace(old_container, new_container, 1)
    print("  ✅ تم ضبط ارتفاع الجدول")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ تم التعديل!")