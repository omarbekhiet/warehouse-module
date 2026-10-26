"""
إصلاح قوالب Excel حسب الأعمدة الفعلية
"""
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'warehouse.db')
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 إصلاح قوالب Excel")
print("=" * 60)

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# إصلاح قالب items
# ============================================
old_items_sql = """SELECT code as 'الكود', name_ar as 'الاسم', unit as 'الوحدة',
                       cost_price as 'سعر التكلفة', sell_price as 'سعر البيع',
                       reorder_level as 'حد الطلب'
                FROM items
                ORDER BY code"""

new_items_sql = """SELECT 
                    i.code as 'الكود',
                    i.name_ar as 'الاسم',
                    i.name_en as 'الاسم إنجليزي',
                    i.barcode as 'الباركود',
                    i.item_type as 'النوع',
                    COALESCE(g.name_ar, '') as 'المجموعة',
                    COALESCE(u.name_ar, '') as 'الوحدة',
                    i.reorder_level as 'حد الطلب'
                FROM items i
                LEFT JOIN item_groups g ON i.group_id = g.id
                LEFT JOIN units_of_measure u ON i.base_uom_id = u.id
                ORDER BY i.code"""

if old_items_sql in content:
    content = content.replace(old_items_sql, new_items_sql)
    print("  ✅ تم إصلاح قالب items (النمط 1)")
else:
    # جرّب نمط آخر
    pattern = r"(SELECT code as 'الكود', name_ar as 'الاسم',)[^;]*?(FROM items[^Z]*)"
    # استخدم البحث المباشر
    if "unit as 'الوحدة'" in content:
        # ابحث عن كل occurrences
        old = "unit as 'الوحدة'"
        content = content.replace(old, "u.name_ar as 'الوحدة'")
        print("  ✅ تم إصلاح items (نمط 2)")

# استبدل كل occurrence لـ items SQL
content = content.replace("""SELECT code as 'الكود', name_ar as 'الاسم', unit as 'الوحدة',
                  cost_price as 'التكلفة', sell_price as 'سعر البيع' FROM items ORDER BY code""",
new_items_sql)

content = content.replace("""SELECT code as 'الكود', name_ar as 'الاسم', 
                       barcode as 'الباركود', unit as 'الوحدة',
                       cost_price as 'سعر التكلفة', sell_price as 'سعر البيع',
                       reorder_level as 'حد الطلب'
                FROM items
                ORDER BY code""",
new_items_sql)

# ============================================
# أصلح باقي القوالب
# ============================================
print("\n📋 فحص باقي القوالب...")

# قائمة القوالب للفحص
templates_to_check = {
    'accounts': ['code', 'name_ar', 'name_en', 'level', 'nature', 'parent_code', 'financial_statement'],
    'customers': ['code', 'name_ar', 'phone', 'email', 'tax_number', 'credit_limit', 'payment_terms'],
    'suppliers': ['code', 'name_ar', 'phone', 'email', 'tax_number', 'credit_limit'],
    'warehouses': ['code', 'name_ar', 'address', 'phone'],
    'item_groups': ['code', 'name_ar'],
    'uom': ['code', 'name_ar'],
}

conn = sqlite3.connect(DB_PATH)

for table, expected_cols in templates_to_check.items():
    cur = conn.execute(f"PRAGMA table_info({table})")
    actual_cols = [r[1] for r in cur.fetchall()]
    missing = [c for c in expected_cols if c not in actual_cols]
    if missing:
        print(f"  ⚠️ {table}: ناقص {', '.join(missing)}")
    else:
        print(f"  ✅ {table}: كل الأعمدة موجودة")

conn.close()

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")