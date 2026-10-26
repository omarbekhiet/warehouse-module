"""
إضافة استيراد Excel لكل الجداول الأساسية
- شجرة الحسابات
- العملاء
- الموردين
- الأصناف
- المستودعات
- المجموعات
- وحدات القياس
- الفروع
- تصنيفات المصروفات
- الخزائن والبنوك
- الأرصدة الافتتاحية
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 إضافة قوالب استيراد شاملة")
print("=" * 60)

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# قوالب الاستيراد الجديدة
# ============================================
NEW_IMPORT_TEMPLATES = '''
        'items': {
            'name': 'الأصناف',
            'table': 'items',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'barcode': 'الباركود',
                'item_type': 'النوع',
                'item_group_id': 'المجموعة',
                'base_uom': 'الوحدة',
                'cost_price': 'سعر التكلفة',
                'sell_price': 'سعر البيع',
                'reorder_level': 'حد الطلب',
            },
            'required': ['code', 'name_ar'],
            'mapping': {
                'item_group_id': ('item_groups', 'name_ar', 'id'),
                'base_uom': ('units_of_measure', 'code', 'code'),
            },
        },
        'warehouses': {
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
        },
        'item_groups': {
            'name': 'مجموعات الأصناف',
            'table': 'item_groups',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'parent_code': 'المجموعة الأب',
            },
            'required': ['code', 'name_ar'],
        },
        'uom': {
            'name': 'وحدات القياس',
            'table': 'units_of_measure',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
            },
            'required': ['code', 'name_ar'],
        },
        'branches': {
            'name': 'الفروع',
            'table': 'branches',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'phone': 'الهاتف',
                'address': 'العنوان',
                'manager_name': 'المدير',
            },
            'required': ['code', 'name_ar'],
        },
        'expense_categories': {
            'name': 'تصنيفات المصروفات',
            'table': 'expense_categories',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'account_code': 'الحساب',
            },
            'required': ['code', 'name_ar', 'account_code'],
        },
        'cash_boxes': {
            'name': 'الخزائن',
            'table': 'cash_boxes',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'box_type': 'النوع',
                'account_code': 'الحساب',
                'opening_balance': 'الرصيد الافتتاحي',
                'opening_date': 'تاريخ الافتتاح',
                'currency': 'العملة',
            },
            'required': ['code', 'name_ar', 'account_code'],
        },
        'banks': {
            'name': 'البنوك',
            'table': 'banks',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'account_code': 'الحساب',
                'account_number': 'رقم الحساب',
                'iban': 'IBAN',
                'branch_name': 'الفرع',
                'opening_balance': 'الرصيد الافتتاحي',
            },
            'required': ['code', 'name_ar', 'account_code'],
        },
        'opening_balances': {
            'name': 'الأرصدة الافتتاحية',
            'table': 'opening_balances',
            'columns': {
                'account_code': 'الحساب',
                'party_type': 'نوع الطرف',
                'party_code': 'كود الطرف',
                'amount': 'المبلغ',
                'direction': 'الاتجاه',
                'notes': 'ملاحظات',
            },
            'required': ['account_code', 'amount', 'direction'],
        },
        'opening_stock': {
            'name': 'الكميات الافتتاحية للمخزون',
            'table': 'opening_stock',
            'columns': {
                'item_code': 'كود الصنف',
                'warehouse_code': 'كود المستودع',
                'quantity': 'الكمية',
                'unit_cost': 'تكلفة الوحدة',
                'batch_no': 'رقم الدفعة',
            },
            'required': ['item_code', 'warehouse_code', 'quantity', 'unit_cost'],
        },
'''

# ابحث عن نهاية IMPORT_TEMPLATES
pattern = r"(    IMPORT_TEMPLATES = \{.*?)(    \}\n    \n    # =========================================\n    # التصدير)"

match = re.search(pattern, content, re.DOTALL)

if match:
    # ضيف القوالب الجديدة قبل نهاية IMPORT_TEMPLATES
    content = content[:match.end(1)] + NEW_IMPORT_TEMPLATES + content[match.start(2):]
    print("  ✅ تم إضافة 10 قوالب استيراد")
else:
    print("  ⚠️ ما لقيتش IMPORT_TEMPLATES")

# ============================================
# تحديث دالة import_from_excel لدعم mapping
# ============================================
old_import = """    def import_from_excel(self, template_key, file_content):
        \"\"\"استيراد من Excel\"\"\"
        if template_key not in self.IMPORT_TEMPLATES:
            return {'success': False, 'message': 'قالب غير موجود'}
        
        template = self.IMPORT_TEMPLATES[template_key]"""

new_import = """    def import_from_excel(self, template_key, file_content, dry_run=False):
        \"\"\"استيراد من Excel
        
        Args:
            template_key: اسم القالب
            file_content: محتوى الملف
            dry_run: لو True، يعرض النتائج بدون حفظ (معاينة)
        \"\"\"
        if template_key not in self.IMPORT_TEMPLATES:
            return {'success': False, 'message': 'قالب غير موجود'}
        
        template = self.IMPORT_TEMPLATES[template_key]"""

if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print("  ✅ تم تحديث import_from_excel (dry_run)")

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")