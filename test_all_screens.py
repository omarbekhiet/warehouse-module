"""
اختبار شامل لكل شاشات المشروع
"""
import urllib.request
import urllib.error
import json
import os
import sys

API = 'http://localhost:5000'
STATIC = f'{API}/static'

# ============================================
# قائمة كل الشاشات
# ============================================
SCREENS = [
    # الأساسية
    ('index.html', 'الرئيسية'),
    ('login.html', 'تسجيل الدخول'),
    ('notifications.html', 'الإشعارات'),
    
    # البيانات الأساسية
    ('warehouses.html', 'المستودعات'),
    ('items.html', 'الأصناف'),
    ('item_groups.html', 'مجموعات الأصناف'),
    ('uom.html', 'وحدات القياس'),
    ('suppliers.html', 'الموردون'),
    ('customers.html', 'العملاء'),
    ('accounts.html', 'الدليل المحاسبي'),
    
    # المشتريات
    ('requisitions.html', 'طلبات الاحتياج'),
    ('purchase_orders.html', 'أوامر الشراء'),
    ('purchase_invoices.html', 'فواتير الشراء'),
    ('payments.html', 'مدفوعات الموردين'),
    ('payment_methods.html', 'طرق الدفع'),
    ('settlements.html', 'التسويات'),
    ('purchase_returns.html', 'مرتجع شراء'),
    ('receipts.html', 'الاستلام'),
    
    # المبيعات
    ('sales_invoices.html', 'فواتير البيع'),
    ('customer_receipts.html', 'تحصيلات العملاء'),
    ('sales_returns.html', 'مرتجع بيع'),
    ('issues.html', 'الصرف'),
    
    # المخازن
    ('material_requests.html', 'طلبات الصرف'),
    ('transfers.html', 'التحويلات'),
    ('counts.html', 'الجرد'),
    ('stock_adjustments.html', 'التسويات المخزنية'),
    ('adjustments_report.html', 'تقرير التسويات'),
    ('inventory_by_warehouse.html', 'المخزون حسب المستودع'),
    
    # المحاسبة (الجديدة + القديمة)
    ('journal.html', 'القيود'),
    ('clearing.html', 'الحسابات الوسيطة'),
    ('financial_reports.html', 'التقارير المالية'),
    ('cash_boxes.html', 'الخزائن والبنوك'),
    ('cash_box_transactions.html', 'حركات الخزائن'),
    ('expenses.html', 'صرف النثريات'),
    ('expense_categories.html', 'تصنيفات المصروفات'),
    ('bank_reconciliation.html', 'التسوية البنكية'),
    ('cash_box_reports.html', 'تقارير الخزائن'),
    ('branches.html', 'الفروع'),
    ('movements_journal.html', 'ربط الحركات بالقيود'),
    
    # التقارير
    ('reports.html', 'تقارير المخازن'),
    ('batches_report.html', 'تقارير الدفعات'),
    ('supplier_rating.html', 'تقييم الموردين'),
    ('price_comparison.html', 'مقارنة الأسعار'),
    ('supplier_balances.html', 'أرصدة الموردين'),
    ('customer_balances.html', 'أرصدة العملاء'),
    ('supplier_statement.html', 'كشف حساب مورد'),
    ('customer_statement.html', 'كشف حساب عميل'),
    
    # الإعدادات
    ('settings.html', 'إعدادات النظام'),
    ('settings_company.html', 'إعدادات الشركة'),
    ('settings_accounting.html', 'إعدادات المحاسبة'),
    ('settings_cash.html', 'إعدادات النقدية'),
    ('settings_inventory.html', 'إعدادات المخزون'),
    ('settings_suppliers.html', 'إعدادات الموردين'),
    ('settings_customers.html', 'إعدادات العملاء'),
    ('settings_users.html', 'إعدادات المستخدمين'),
    ('settings_print.html', 'إعدادات الطباعة'),
    ('company_config.html', 'إعدادات الشركة'),
    
    # الطباعة
    ('print_center.html', 'مركز الطباعة'),
    ('print_statement.html', 'طباعة كشف حساب'),
    ('print_financial_report.html', 'طباعة تقرير مالي'),
    ('print_purchase_invoice.html', 'طباعة فاتورة شراء'),
    ('print_sales_invoice.html', 'طباعة فاتورة بيع'),
    ('print_receipt.html', 'طباعة إيصال'),
    ('print_issue.html', 'طباعة صرف'),
    ('print_transfer.html', 'طباعة تحويل'),
    ('print_purchase_order.html', 'طباعة أمر شراء'),
    ('print_report.html', 'طباعة تقرير'),
]

# ============================================
# قائمة APIs
# ============================================
APIS = [
    ('/api/v1/accounts/', 'الحسابات'),
    ('/api/v1/warehouses/', 'المستودعات'),
    ('/api/v1/items/', 'الأصناف'),
    ('/api/v1/groups/', 'المجموعات'),
    ('/api/v1/suppliers/', 'الموردون'),
    ('/api/v1/customers/', 'العملاء'),
    ('/api/v1/purchase-invoices/', 'فواتير الشراء'),
    ('/api/v1/sales-invoices/', 'فواتير البيع'),
    ('/api/v1/payments/payments/', 'المدفوعات'),
    ('/api/v1/payments/receipts/', 'التحصيلات'),
    ('/api/v1/payments/methods/', 'طرق الدفع'),
    ('/api/v1/cash-boxes/stats', 'إحصائيات الخزائن'),
    ('/api/v1/cash-boxes/boxes/', 'الخزائن'),
    ('/api/v1/cash-boxes/banks/', 'البنوك'),
    ('/api/v1/cash-boxes/cards/', 'البطاقات'),
    ('/api/v1/cash-boxes/transactions/', 'الحركات'),
    ('/api/v1/cash-boxes/branches/', 'الفروع'),
    ('/api/v1/cash-boxes/tax-settings/', 'الضرائب'),
    ('/api/v1/cash-boxes/discount-settings/', 'الخصومات'),
    ('/api/v1/cash-boxes/reconciliations/', 'التسويات البنكية'),
    ('/api/v1/cash-boxes/link/stats', 'إحصائيات الربط'),
    ('/api/v1/cash-boxes/link/movements-with-journals', 'الحركات مع القيود'),
    ('/api/v1/expenses/categories/', 'تصنيفات المصروفات'),
    ('/api/v1/expenses/expenses/', 'المصروفات'),
    ('/api/v1/expenses/stats', 'إحصائيات المصروفات'),
]

# ============================================
# دوال الاختبار
# ============================================

def test_url(url, timeout=5):
    """يختبر URL ويرجع (status, message)"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (r.status, 'OK')
    except urllib.error.HTTPError as e:
        return (e.code, f'HTTP {e.code}')
    except urllib.error.URLError as e:
        return (0, f'Connection Error: {e.reason}')
    except Exception as e:
        return (0, str(e)[:50])

# ============================================
# التشغيل
# ============================================

def main():
    print("=" * 70)
    print("🧪 اختبار شامل للمشروع")
    print("=" * 70)
    print()
    
    # 1. اختبار الاتصال
    print("🔌 اختبار الاتصال بالسيرفر...")
    status, msg = test_url(f'{API}/')
    if status == 0:
        print(f"  ❌ السيرفر مش شغال: {msg}")
        print("\n  شغّل السيرفر أولاً:")
        print("    cd J:\\warehouse-module")
        print("    python run.py")
        return
    print(f"  ✅ السيرفر شغال (status {status})")
    print()
    
    # 2. اختبار الشاشات
    print("=" * 70)
    print("📄 اختبار الشاشات (HTML)")
    print("=" * 70)
    
    screens_ok = 0
    screens_fail = 0
    failed_screens = []
    
    for screen, name in SCREENS:
        url = f'{API}/{screen}'
        status, msg = test_url(url)
        
        if status == 200:
            print(f"  ✅ {name:35} — {screen}")
            screens_ok += 1
        else:
            print(f"  ❌ {name:35} — {screen} ({msg})")
            screens_fail += 1
            failed_screens.append((screen, name, msg))
    
    print()
    print(f"  📊 نجح: {screens_ok}/{len(SCREENS)}")
    
    # 3. اختبار APIs
    print()
    print("=" * 70)
    print("🔌 اختبار APIs")
    print("=" * 70)
    
    apis_ok = 0
    apis_fail = 0
    failed_apis = []
    
    for api, name in APIS:
        url = f'{API}{api}'
        status, msg = test_url(url)
        
        if status == 200:
            print(f"  ✅ {name:35} — {api}")
            apis_ok += 1
        else:
            print(f"  ❌ {name:35} — {api} ({msg})")
            apis_fail += 1
            failed_apis.append((api, name, msg))
    
    print()
    print(f"  📊 نجح: {apis_ok}/{len(APIS)}")
    
    # 4. ملخص
    print()
    print("=" * 70)
    print("📊 ملخص")
    print("=" * 70)
    print(f"  📄 الشاشات: {screens_ok}/{len(SCREENS)}")
    print(f"  🔌 الـ APIs: {apis_ok}/{len(APIS)}")
    print(f"  📈 الإجمالي: {screens_ok + apis_ok}/{len(SCREENS) + len(APIS)}")
    
    # 5. الشاشات الناقصة
    if failed_screens:
        print()
        print("=" * 70)
        print("⚠️ شاشات فاشلة")
        print("=" * 70)
        for screen, name, msg in failed_screens:
            print(f"  ❌ {name} ({screen}) — {msg}")
    
    if failed_apis:
        print()
        print("=" * 70)
        print("⚠️ APIs فاشلة")
        print("=" * 70)
        for api, name, msg in failed_apis:
            print(f"  ❌ {name} ({api}) — {msg}")
    
    # النتيجة
    print()
    if not failed_screens and not failed_apis:
        print("🎉 ممتاز! كل الشاشات والـ APIs شغالة 100%")
    elif len(failed_screens) + len(failed_apis) < 5:
        print("✅ ممتاز — فيه مشاكل قليلة")
    else:
        print("⚠️ فيه مشاكل محتاجة مراجعة")


if __name__ == '__main__':
    main()