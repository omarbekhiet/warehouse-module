"""
مراجعة وربط كل الملفات الناقصة في index.html
- فحص كل ملفات HTML
- فحص اللي موجود في index.html
- تحديد الناقص
- تحديد المكسور (404)
- ربط الناقص
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')
INDEX_PATH = os.path.join(STATIC, 'index.html')

print("=" * 70)
print("🔗 مراجعة وربط الملفات الناقصة")
print("=" * 70)

# ============================================
# 1. كل ملفات HTML الموجودة
# ============================================
all_html = sorted([f for f in os.listdir(STATIC) if f.endswith('.html')])
print(f"\n📊 إجمالي ملفات HTML: {len(all_html)}")

# ============================================
# 2. شاشات لا تحتاج ربط
# ============================================
SKIP_LINKING = {
    'index.html',          # الشاشة الرئيسية
    'index_1.html',        # نسخة قديمة
    'login.html',          # تسجيل الدخول
    'data_io.html',        # مركز الاستيراد/التصدير (نضيفه)
    'movements_journal.html',  # نضيفه في المحاسبة
}

# ============================================
# 3. شاشات الطباعة (تنفتح من شاشات تانية)
# ============================================
PRINT_SCREENS = {
    'print_statement.html',
    'print_financial_report.html',
    'print_purchase_invoice.html',
    'print_sales_invoice.html',
    'print_receipt.html',
    'print_issue.html',
    'print_transfer.html',
    'print_purchase_order.html',
    'print_report.html',
    'print_adjustment.html',
    'print_center.html',
}

# ============================================
# 4. قراءة index.html
# ============================================
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    index_content = f.read()

# ============================================
# 5. استخراج الملفات المربوطة
# ============================================
linked_files = set()
# ابحث عن href="X.html"
matches = re.findall(r'href="([^"]+\.html)"', index_content)
for m in matches:
    linked_files.add(m)

print(f"\n📊 الملفات المربوطة في index.html: {len(linked_files)}")

# ============================================
# 6. تحديد الناقص
# ============================================
missing = []
for f in all_html:
    if f in linked_files:
        continue
    if f in PRINT_SCREENS:
        continue
    if f in SKIP_LINKING:
        continue
    missing.append(f)

print(f"\n📊 الملفات الناقصة (غير مربوطة): {len(missing)}")
for f in missing:
    print(f"  • {f}")

# ============================================
# 7. تحديد المكسور (مربوط بس مش موجود)
# ============================================
broken = []
for f in linked_files:
    if f.startswith('http'):
        continue
    if not os.path.exists(os.path.join(STATIC, f)):
        broken.append(f)

print(f"\n📊 الملفات المكسورة (مربوطة بس مش موجودة): {len(broken)}")
for f in broken:
    print(f"  ❌ {f}")

# ============================================
# 8. تصنيف الناقص حسب القسم
# ============================================
CATEGORIES = {
    'البيانات الأساسية': ['accounts', 'warehouses', 'items', 'item_groups', 'uom', 'suppliers', 'customers'],
    'المشتريات': ['requisitions', 'purchase_orders', 'purchase_invoices', 'payments', 'payment_methods', 'settlements', 'purchase_returns', 'receipts'],
    'المبيعات': ['sales_invoices', 'customer_receipts', 'sales_returns', 'issues'],
    'المخازن': ['material_requests', 'transfers', 'counts', 'stock_adjustments', 'adjustments_report', 'inventory_by_warehouse'],
    'المحاسبة': ['accounts', 'journal', 'clearing', 'financial_reports', 'cash_boxes', 'cash_box_transactions', 'expenses', 'expense_categories', 'bank_reconciliation', 'cash_box_reports', 'branches', 'movements_journal'],
    'التقارير': ['reports', 'batches_report', 'supplier_rating', 'price_comparison', 'supplier_balances', 'customer_balances', 'supplier_statement', 'customer_statement'],
    'الإعدادات': ['settings', 'settings_company', 'settings_accounting', 'settings_cash', 'settings_inventory', 'settings_suppliers', 'settings_customers', 'settings_users', 'settings_print'],
}

# ============================================
# 9. عرض التقرير
# ============================================
print("\n" + "=" * 70)
print("📊 التقرير النهائي")
print("=" * 70)

print(f"""
  📁 إجمالي ملفات HTML: {len(all_html)}
  ✅ مربوطة في index.html: {len(linked_files)}
  ❌ ناقصة (غير مربوطة): {len(missing)}
  💥 مكسورة (مربوطة بس مش موجودة): {len(broken)}
  🖨️ شاشات طباعة (منفصلة): {len(PRINT_SCREENS)}
  📄 الشاشات المستثناة: {len(SKIP_LINKING)}
""")

# حفظ التقرير
report_path = os.path.join(BASE, 'linking_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("تقرير ربط الملفات\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"إجمالي: {len(all_html)}\n")
    f.write(f"مربوطة: {len(linked_files)}\n")
    f.write(f"ناقصة: {len(missing)}\n")
    f.write(f"مكسورة: {len(broken)}\n\n")
    
    if missing:
        f.write("الملفات الناقصة:\n")
        for m in missing:
            f.write(f"  • {m}\n")
    
    if broken:
        f.write("\nالملفات المكسورة:\n")
        for b in broken:
            f.write(f"  ❌ {b}\n")

print(f"📄 التقرير محفوظ: {report_path}")

# ============================================
# 10. إصلاح المكسور
# ============================================
if broken:
    print(f"\n🔧 إصلاح الملفات المكسورة...")
    for f in broken:
        # شيل الرابط
        pattern = rf'\s*<a href="{re.escape(f)}"[^>]*>.*?</a>'
        matches = re.findall(pattern, index_content, re.DOTALL)
        if matches:
            for m in matches:
                index_content = index_content.replace(m, '', 1)
            print(f"  ✅ تم شيل رابط: {f}")
    
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"  ✅ تم حفظ index.html")