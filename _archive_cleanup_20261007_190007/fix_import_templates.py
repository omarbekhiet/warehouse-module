"""
إصلاح قوالب الاستيراد:
- suppliers: شيل credit_limit
- warehouses: شيل address + phone
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 إصلاح قوالب الاستيراد")
print("=" * 60)

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. إصلاح suppliers
# ============================================
old_suppliers = """'suppliers': {
            'name': 'الموردين',
            'table': 'suppliers',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'phone': 'الهاتف',
                'email': 'البريد',
                'tax_number': 'الرقم الضريبي',
                'credit_limit': 'حد الائتمان',
            },
            'required': ['code', 'name_ar'],
        },"""

new_suppliers = """'suppliers': {
            'name': 'الموردين',
            'table': 'suppliers',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'phone': 'الهاتف',
                'email': 'البريد',
                'tax_number': 'الرقم الضريبي',
                'payment_terms': 'مدة السداد',
            },
            'required': ['code', 'name_ar'],
        },"""

if old_suppliers in content:
    content = content.replace(old_suppliers, new_suppliers)
    print("  ✅ تم إصلاح suppliers (شيل credit_limit)")
else:
    # جرّب نمط مرن
    old_pat = r"'suppliers':\s*\{.*?'credit_limit':\s*'حد الائتمان',.*?\}"
    if re.search(old_pat, content, re.DOTALL):
        # استبدل credit_limit
        content = re.sub(
            r"'credit_limit':\s*'حد الائتمان',",
            "",
            content,
            count=1
        )
        print("  ✅ تم شيل credit_limit من suppliers (نمط 2)")
    else:
        print("  ⚠️ ما لقيتش suppliers")

# ============================================
# 2. إصلاح warehouses
# ============================================
old_warehouses = """'warehouses': {
            'name': 'المستودعات',
            'table': 'warehouses',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'address': 'العنوان',
                'phone': 'الهاتف',
            },
            'required': ['code', 'name_ar'],
        },"""

new_warehouses = """'warehouses': {
            'name': 'المستودعات',
            'table': 'warehouses',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'warehouse_type': 'النوع',
                'location': 'الموقع',
                'account_code': 'الحساب',
            },
            'required': ['code', 'name_ar'],
        },"""

if old_warehouses in content:
    content = content.replace(old_warehouses, new_warehouses)
    print("  ✅ تم إصلاح warehouses (شيل address + phone)")
else:
    # جرّب نمط مرن
    old_pat = r"'warehouses':\s*\{.*?'address':\s*'العنوان',.*?'phone':\s*'الهاتف',.*?\}"
    if re.search(old_pat, content, re.DOTALL):
        content = re.sub(r"'address':\s*'العنوان',", "", content, count=1)
        content = re.sub(r"'phone':\s*'الهاتف',", "", content, count=1)
        print("  ✅ تم إصلاح warehouses (نمط 2)")
    else:
        print("  ⚠️ ما لقيتش warehouses")

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")