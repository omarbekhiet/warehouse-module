"""
إضافة حقل الخزينة في HTML - نسخة دقيقة
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'payments.html')

print("=" * 60)
print("🔧 إضافة حقل الخزينة في HTML")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# السطر المميز (طريقة السداد)
old = '        <div class="col-md-4"><label class="form-label">طريقة السداد *</label><select class="form-select" id="f-method" onchange="onMethodChange()"></select></div>'

# السطر الجديد (مع حقل الخزينة)
new = old + '\n        <div class="col-md-4"><label class="form-label">الخزينة/البنك</label><select class="form-select" id="f-cash-box"><option value="">— بدون —</option></select></div>'

if '<select class="form-select" id="f-cash-box"' in content:
    print("  ℹ️ حقل الخزينة موجود بالفعل في HTML")
elif old in content:
    content = content.replace(old, new, 1)
    print("  ✅ تم إضافة حقل الخزينة في HTML")
else:
    print("  ❌ السطر المميز مش موجود")
    print()
    print("  ابحث يدوياً عن:")
    print(f"  {repr(old[:80])}...")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
has_html = '<select class="form-select" id="f-cash-box"' in content
has_js = "getElementById('f-cash-box')" in content
print(f"  HTML: {'✅' if has_html else '❌'}")
print(f"  JavaScript: {'✅' if has_js else '❌'}")