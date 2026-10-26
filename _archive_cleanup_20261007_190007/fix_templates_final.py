"""
إصلاح القوالب حسب الأعمدة الفعلية - نسخة نهائية
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 إصلاح القوالب النهائي")
print("=" * 60)

# ============================================
# القوالب المصححة
# ============================================
FIXED_TEMPLATES = {
    'suppliers': {
        'name': 'الموردين',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي',
                       COALESCE(phone, '') as 'الهاتف',
                       COALESCE(email, '') as 'البريد',
                       COALESCE(tax_number, '') as 'الرقم الضريبي',
                       COALESCE(payment_terms, 0) as 'مدة السداد',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM suppliers
                ORDER BY code""",
    },
    'warehouses': {
        'name': 'المستودعات',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي',
                       COALESCE(warehouse_type, '') as 'النوع',
                       COALESCE(location, '') as 'الموقع',
                       COALESCE(account_code, '') as 'الحساب',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM warehouses
                ORDER BY code""",
    },
    'item_groups': {
        'name': 'مجموعات الأصناف',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي',
                       COALESCE(level, 1) as 'المستوى',
                       COALESCE(default_cost_method, '') as 'طريقة التكلفة',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM item_groups
                ORDER BY code""",
    },
    'banks': {
        'name': 'البنوك',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي',
                       account_code as 'الحساب',
                       COALESCE(account_number, '') as 'رقم الحساب',
                       COALESCE(iban, '') as 'IBAN',
                       COALESCE(swift_code, '') as 'SWIFT',
                       COALESCE(branch_name, '') as 'الفرع',
                       COALESCE(current_balance, 0) as 'الرصيد',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM banks
                ORDER BY code""",
    },
    'branches': {
        'name': 'الفروع',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي',
                       COALESCE(phone, '') as 'الهاتف',
                       COALESCE(manager_name, '') as 'المدير',
                       COALESCE(address, '') as 'العنوان',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM branches
                ORDER BY code""",
    },
    'purchase_returns': {
        'name': 'مرتجع شراء',
        'sql': """SELECT pr.return_no as 'رقم المرتجع', 
                       pr.return_date as 'التاريخ',
                       COALESCE(s.name_ar, '') as 'المورد',
                       COALESCE(w.name_ar, '') as 'المستودع',
                       COALESCE(pr.total_amount, 0) as 'الإجمالي',
                       COALESCE(pr.status, '') as 'الحالة'
                FROM purchase_returns pr
                LEFT JOIN suppliers s ON pr.supplier_id = s.id
                LEFT JOIN warehouses w ON pr.warehouse_id = w.id
                ORDER BY pr.return_date DESC, pr.id DESC
                LIMIT 500""",
    },
    'sales_returns': {
        'name': 'مرتجع بيع',
        'sql': """SELECT sr.return_no as 'رقم المرتجع',
                       sr.return_date as 'التاريخ',
                       COALESCE(c.name_ar, '') as 'العميل',
                       COALESCE(w.name_ar, '') as 'المستودع',
                       COALESCE(sr.total_amount, 0) as 'الإجمالي',
                       COALESCE(sr.status, '') as 'الحالة'
                FROM sales_returns sr
                LEFT JOIN customers c ON sr.customer_id = c.id
                LEFT JOIN warehouses w ON sr.warehouse_id = w.id
                ORDER BY sr.return_date DESC, sr.id DESC
                LIMIT 500""",
    },
    'inventory_counts': {
        'name': 'الجرد',
        'sql': """SELECT ic.count_no as 'رقم الجرد',
                       ic.count_date as 'التاريخ',
                       COALESCE(w.name_ar, '') as 'المستودع',
                       COALESCE(ic.count_type, '') as 'النوع',
                       COALESCE(ic.status, '') as 'الحالة',
                       COALESCE(je.entry_no, '') as 'رقم القيد'
                FROM inventory_counts ic
                LEFT JOIN warehouses w ON ic.warehouse_id = w.id
                LEFT JOIN journal_entries je ON ic.journal_entry_id = je.id
                ORDER BY ic.count_date DESC, ic.id DESC
                LIMIT 500""",
    },
}

# ============================================
# قراءة الملف
# ============================================
with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# استبدال كل قالب
# ============================================
for key, template in FIXED_TEMPLATES.items():
    # ابحث عن القالب في EXPORT_TEMPLATES
    pattern = rf"('{key}':\s*\{{\s*'name':\s*'[^']+',\s*'sql':\s*\"\"\").*?(\"\"\",\s*'columns':\s*\[)"
    
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # استبدل الـ sql فقط
        sql_escaped = template['sql'].strip()
        new_content = content[:match.start(1)] + \
                     f"'{key}': {{\n            'name': '{template['name']}',\n            'sql': \"\"\"{sql_escaped}\"\"\"," + \
                     content[match.start(2) + len('"""'):]
        content = new_content
        print(f"  ✅ تم إصلاح: {key}")
    else:
        # جرّب نمط آخر
        alt_pattern = rf"('{key}':\s*\{{\s*'name':\s*'[^']+',\s*'sql':\s*\"\"\").*?(\"\"\")"
        alt_match = re.search(alt_pattern, content, re.DOTALL)
        if alt_match:
            sql_escaped = template['sql'].strip()
            content = content[:alt_match.start()] + \
                     f"'{key}': {{\n            'name': '{template['name']}',\n            'sql': \"\"\"{sql_escaped}\"\"\"" + \
                     content[alt_match.end():]
            print(f"  ✅ تم إصلاح: {key} (نمط 2)")
        else:
            print(f"  ⚠️ ما لقيتش: {key}")

# ============================================
# حفظ
# ============================================
with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================
# اختبار
# ============================================
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")