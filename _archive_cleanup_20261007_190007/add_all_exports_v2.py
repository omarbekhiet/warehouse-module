"""
إضافة زر تصدير Excel لكل شاشات التقارير
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')

# ============================================
# الشاشات المطلوبة مع القوالب
# ============================================
SCREENS_WITH_TEMPLATES = {
    'warehouses.html': 'warehouses',
    'item_groups.html': 'item_groups',
    'uom.html': 'uom',
    'supplier_balances.html': 'supplier_balances',
    'customer_balances.html': 'customer_balances',
    'settlements.html': 'settlements',
    'purchase_orders.html': 'purchase_orders',
    'requisitions.html': 'requisitions',
    'receipts.html': 'receipts',
    'issues.html': 'issues',
    'transfers.html': 'transfers',
    'counts.html': 'counts',
    'material_requests.html': 'material_requests',
    'stock_adjustments.html': 'stock_adjustments',
    'payment_methods.html': 'payment_methods',
    'clearing.html': 'clearing',
    'financial_reports.html': 'financial_reports',
    'reports.html': 'reports',
    'item_movement.html': 'item_movement',
    'inventory_by_warehouse.html': 'inventory_by_warehouse',
    'supplier_rating.html': 'supplier_rating',
    'price_comparison.html': 'price_comparison',
    'supplier_statement.html': 'supplier_statement',
    'customer_statement.html': 'customer_statement',
    'batches_report.html': 'batches_report',
    'adjustments_report.html': 'adjustments_report',
    'movements_journal.html': 'movements_journal',
}

# ============================================
# الشاشات اللي مش محتاجة تصدير
# ============================================
SKIP = {
    'index.html', 'index_1.html', 'login.html', 'notifications.html',
    'data_io.html', 'bank_reconciliation.html', 'print_center.html',
    'settings.html',
    # settings_*
    'settings_company.html', 'settings_accounting.html', 'settings_cash.html',
    'settings_inventory.html', 'settings_suppliers.html', 'settings_customers.html',
    'settings_users.html', 'settings_print.html',
    # print_*
    'print_statement.html', 'print_financial_report.html', 'print_purchase_invoice.html',
    'print_sales_invoice.html', 'print_receipt.html', 'print_issue.html',
    'print_transfer.html', 'print_purchase_order.html', 'print_report.html',
    'print_adjustment.html',
    # مضاف
    'accounts.html', 'customers.html', 'suppliers.html', 'items.html',
    'cash_boxes.html', 'journal.html', 'payments.html',
    'customer_receipts.html', 'cash_box_transactions.html', 'expenses.html',
    'purchase_invoices.html', 'sales_invoices.html', 'purchase_returns.html',
    'sales_returns.html', 'branches.html', 'expense_categories.html',
}

# ============================================
# دالة زر التصدير
# ============================================
def get_button(template_key):
    return f'''<button class="btn btn-sm btn-outline-success" onclick="exportToExcel('{template_key}')" title="تصدير Excel">
                <i class="bi bi-file-earmark-excel"></i> Excel
            </button>'''

def get_js():
    return '''
<script>
function exportToExcel(templateKey) {
    if (!templateKey) return;
    window.location.href = `/api/v1/export/excel/export/${templateKey}`;
}
</script>
'''

# ============================================
# التشغيل
# ============================================
print("=" * 60)
print("🔧 إضافة أزرار التصدير للشاشات الناقصة")
print("=" * 60)

total = 0
skipped = 0
errors = []

for screen, template in SCREENS_WITH_TEMPLATES.items():
    if screen in SKIP:
        continue
    
    path = os.path.join(STATIC, screen)
    
    if not os.path.exists(path):
        print(f"  ⏭️ {screen}: مش موجود")
        skipped += 1
        continue
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'exportToExcel' in content:
            print(f"  ℹ️ {screen}: موجود")
            skipped += 1
            continue
        
        # ابحث عن مكان الزر
        patterns = [
            r'(<a href="index\.html" class="btn[^"]*"[^>]*>\s*<i class="bi bi-house[^>]*></i>\s*الرئيسية\s*</a>)',
            r'(<a href="index\.html"[^>]*>.*?الرئيسية.*?</a>)',
        ]
        
        button_added = False
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insert_pos = match.start()
                button_html = get_button(template) + '\n            '
                content = content[:insert_pos] + button_html + content[insert_pos:]
                button_added = True
                break
        
        if not button_added:
            errors.append(screen)
            print(f"  ⚠️ {screen}: مفيش مكان")
            continue
        
        if 'exportToExcel' not in content:
            content = content.replace('</body>', get_js() + '\n</body>', 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ {screen}")
        total += 1
    except Exception as e:
        errors.append(screen)
        print(f"  ❌ {screen}: {e}")

print(f"\n  📊 النتيجة: {total} نجح، {skipped} تخطي، {len(errors)} فشل")

# ============================================
# تنبيه للقوالب الناقصة
# ============================================
print("\n" + "=" * 60)
print("⚠️ القوالب المطلوبة في excel_service.py")
print("=" * 60)

service_path = os.path.join(BASE, 'app', 'services', 'excel_service.py')
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

missing_templates = []
for screen, template in SCREENS_WITH_TEMPLATES.items():
    if f"'{template}':" not in service_content:
        missing_templates.append(template)

if missing_templates:
    print(f"\n  ❌ قوالب ناقصة ({len(missing_templates)}):")
    for t in sorted(set(missing_templates)):
        print(f"     • {t}")
    print(f"\n  📌 لازم تضيفهم في excel_service.py")
else:
    print("  ✅ كل القوالب موجودة")