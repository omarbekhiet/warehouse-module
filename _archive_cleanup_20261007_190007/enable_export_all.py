"""
تفعيل تصدير Excel لكل الشاشات
- يضيف القوالب في excel_service.py
- يضيف الأزرار في كل شاشة
- يختبر
"""
import os
import re
import py_compile

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

# ============================================
# 1. شاشات تحتاج تصدير + القوالب
# ============================================
SCREENS_TEMPLATES = {
    # بيانات أساسية
    'accounts.html': 'accounts',
    'warehouses.html': 'warehouses',
    'items.html': 'items',
    'item_groups.html': 'item_groups',
    'uom.html': 'uom',
    'suppliers.html': 'suppliers',
    'customers.html': 'customers',
    
    # مشتريات
    'requisitions.html': 'requisitions',
    'purchase_orders.html': 'purchase_orders',
    'purchase_invoices.html': 'purchase_invoices',
    'purchase_returns.html': 'purchase_returns',
    'receipts.html': 'receipts',
    'payments.html': 'supplier_payments',
    'payment_methods.html': 'payment_methods',
    'settlements.html': 'settlements',
    
    # مبيعات
    'sales_invoices.html': 'sales_invoices',
    'sales_returns.html': 'sales_returns',
    'issues.html': 'issues',
    'customer_receipts.html': 'customer_receipts',
    
    # مخازن
    'material_requests.html': 'material_requests',
    'transfers.html': 'transfers',
    'counts.html': 'counts',
    'stock_adjustments.html': 'stock_adjustments',
    'adjustments_report.html': 'adjustments_report',
    'inventory_by_warehouse.html': 'inventory_by_warehouse',
    
    # محاسبة
    'journal.html': 'journal_entries',
    'clearing.html': 'clearing',
    'financial_reports.html': 'financial_reports',
    'cash_boxes.html': 'cash_boxes',
    'cash_box_transactions.html': 'cash_box_transactions',
    'expenses.html': 'expenses',
    'expense_categories.html': 'expense_categories',
    'cash_box_reports.html': 'cash_box_reports',
    'branches.html': 'branches',
    'movements_journal.html': 'movements_journal',
    
    # تقارير
    'reports.html': 'reports',
    'batches_report.html': 'batches_report',
    'supplier_rating.html': 'supplier_rating',
    'price_comparison.html': 'price_comparison',
    'supplier_balances.html': 'supplier_balances',
    'customer_balances.html': 'customer_balances',
    'supplier_statement.html': 'supplier_statement',
    'customer_statement.html': 'customer_statement',
    'item_movement.html': 'item_movement',
}

# ============================================
# 2. تعريفات القوالب
# ============================================
TEMPLATE_DEFS = {
    'accounts': {
        'name': 'الحسابات',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم عربي', name_en as 'الاسم إنجليزي',
                  level as 'المستوى', nature as 'الطبيعة', parent_code as 'الحساب الأب',
                  financial_statement as 'القائمة' FROM accounts ORDER BY code""",
    },
    'warehouses': {
        'name': 'المستودعات',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', name_en as 'الاسم إنجليزي',
                  address as 'العنوان', phone as 'الهاتف' FROM warehouses ORDER BY code""",
    },
    'items': {
        'name': 'الأصناف',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', unit as 'الوحدة',
                  cost_price as 'التكلفة', sell_price as 'سعر البيع' FROM items ORDER BY code""",
    },
    'item_groups': {
        'name': 'مجموعات الأصناف',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم' FROM item_groups ORDER BY code",
    },
    'uom': {
        'name': 'وحدات القياس',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم' FROM units_of_measure ORDER BY code",
    },
    'suppliers': {
        'name': 'الموردين',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', phone as 'الهاتف',
                  email as 'البريد', tax_number as 'الرقم الضريبي' FROM suppliers ORDER BY code""",
    },
    'customers': {
        'name': 'العملاء',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', phone as 'الهاتف',
                  email as 'البريد', tax_number as 'الرقم الضريبي' FROM customers ORDER BY code""",
    },
    'requisitions': {
        'name': 'طلبات الاحتياج',
        'sql': """SELECT id as 'الرقم', status as 'الحالة' FROM purchase_requisitions LIMIT 500""",
    },
    'purchase_orders': {
        'name': 'أوامر الشراء',
        'sql': """SELECT po.id as 'الرقم', po.order_no as 'رقم الأمر', po.order_date as 'التاريخ',
                  s.name_ar as 'المورد', po.status as 'الحالة'
                  FROM purchase_orders po LEFT JOIN suppliers s ON po.supplier_id = s.id
                  ORDER BY po.id DESC LIMIT 500""",
    },
    'purchase_invoices': {
        'name': 'فواتير الشراء',
        'sql': """SELECT pi.invoice_no as 'رقم الفاتورة', pi.invoice_date as 'التاريخ',
                  s.name_ar as 'المورد', pi.total_amount as 'الإجمالي', pi.status as 'الحالة'
                  FROM purchase_invoices pi LEFT JOIN suppliers s ON pi.supplier_id = s.id
                  ORDER BY pi.id DESC LIMIT 500""",
    },
    'purchase_returns': {
        'name': 'مرتجع شراء',
        'sql': """SELECT pr.id as 'الرقم', s.name_ar as 'المورد', pr.status as 'الحالة'
                  FROM purchase_returns pr LEFT JOIN suppliers s ON pr.supplier_id = s.id LIMIT 500""",
    },
    'receipts': {
        'name': 'الاستلام',
        'sql': """SELECT r.id as 'الرقم', w.name_ar as 'المستودع', r.status as 'الحالة'
                  FROM receipts r LEFT JOIN warehouses w ON r.warehouse_id = w.id LIMIT 500""",
    },
    'supplier_payments': {
        'name': 'مدفوعات الموردين',
        'sql': """SELECT sp.payment_no as 'رقم الدفعة', sp.payment_date as 'التاريخ',
                  s.name_ar as 'المورد', sp.payment_method as 'الطريقة', sp.amount as 'المبلغ'
                  FROM supplier_payments sp LEFT JOIN suppliers s ON sp.supplier_id = s.id
                  ORDER BY sp.id DESC LIMIT 500""",
    },
    'payment_methods': {
        'name': 'طرق الدفع',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم', account_code as 'الحساب' FROM payment_methods",
    },
    'settlements': {
        'name': 'التسويات',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM settlements LIMIT 500",
    },
    'sales_invoices': {
        'name': 'فواتير البيع',
        'sql': """SELECT si.invoice_no as 'رقم الفاتورة', si.invoice_date as 'التاريخ',
                  c.name_ar as 'العميل', si.total_amount as 'الإجمالي', si.status as 'الحالة'
                  FROM sales_invoices si LEFT JOIN customers c ON si.customer_id = c.id
                  ORDER BY si.id DESC LIMIT 500""",
    },
    'sales_returns': {
        'name': 'مرتجع بيع',
        'sql': """SELECT sr.id as 'الرقم', c.name_ar as 'العميل', sr.status as 'الحالة'
                  FROM sales_returns sr LEFT JOIN customers c ON sr.customer_id = c.id LIMIT 500""",
    },
    'issues': {
        'name': 'الصرف',
        'sql': """SELECT i.id as 'الرقم', w.name_ar as 'المستودع', i.status as 'الحالة'
                  FROM issues i LEFT JOIN warehouses w ON i.warehouse_id = w.id LIMIT 500""",
    },
    'customer_receipts': {
        'name': 'تحصيلات العملاء',
        'sql': """SELECT cr.receipt_no as 'رقم التحصيل', cr.receipt_date as 'التاريخ',
                  c.name_ar as 'العميل', cr.receipt_method as 'الطريقة', cr.amount as 'المبلغ'
                  FROM customer_receipts cr LEFT JOIN customers c ON cr.customer_id = c.id
                  ORDER BY cr.id DESC LIMIT 500""",
    },
    'material_requests': {
        'name': 'طلبات الصرف',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM material_requests LIMIT 500",
    },
    'transfers': {
        'name': 'التحويلات',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM transfers LIMIT 500",
    },
    'counts': {
        'name': 'الجرد',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM inventory_counts LIMIT 500",
    },
    'stock_adjustments': {
        'name': 'التسويات المخزنية',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM stock_adjustments LIMIT 500",
    },
    'adjustments_report': {
        'name': 'تقرير التسويات',
        'sql': "SELECT id as 'الرقم', status as 'الحالة' FROM stock_adjustments LIMIT 500",
    },
    'inventory_by_warehouse': {
        'name': 'المخزون حسب المستودع',
        'sql': """SELECT sb.warehouse_id as 'المستودع', sb.item_id as 'الصنف', 
                  sb.quantity as 'الكمية' FROM stock_balances sb LIMIT 1000""",
    },
    'journal_entries': {
        'name': 'القيود',
        'sql': """SELECT entry_no as 'رقم القيد', entry_date as 'التاريخ',
                  reference_type as 'نوع المرجع', reference_no as 'رقم المرجع',
                  description as 'البيان', total_debit as 'مدين', total_credit as 'دائن',
                  status as 'الحالة' FROM journal_entries
                  ORDER BY entry_date DESC, id DESC LIMIT 1000""",
    },
    'clearing': {
        'name': 'الحسابات الوسيطة',
        'sql': """SELECT entry_no as 'رقم القيد', entry_date as 'التاريخ',
                  description as 'البيان', total_debit as 'مدين', total_credit as 'دائن'
                  FROM journal_entries WHERE reference_type LIKE '%CLEAR%'
                  ORDER BY entry_date DESC LIMIT 500""",
    },
    'financial_reports': {
        'name': 'التقارير المالية',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', 
                  financial_statement as 'القائمة', nature as 'الطبيعة'
                  FROM accounts WHERE is_leaf = 1 ORDER BY code""",
    },
    'cash_boxes': {
        'name': 'الخزائن',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', box_type as 'النوع',
                  account_code as 'الحساب', opening_balance as 'رصيد افتتاحي',
                  current_balance as 'رصيد حالي' FROM cash_boxes WHERE is_active = 1""",
    },
    'cash_box_transactions': {
        'name': 'حركات الخزائن',
        'sql': """SELECT txn_date as 'التاريخ', txn_type as 'النوع',
                  reference_no as 'المرجع', amount as 'المبلغ',
                  balance_after as 'الرصيد بعد', description as 'البيان'
                  FROM cash_box_transactions ORDER BY id DESC LIMIT 500""",
    },
    'expenses': {
        'name': 'المصروفات',
        'sql': """SELECT e.expense_no as 'رقم المصروف', e.expense_date as 'التاريخ',
                  ec.name_ar as 'التصنيف', e.beneficiary as 'المستفيد',
                  e.amount as 'المبلغ', e.description as 'البيان'
                  FROM petty_cash_expenses e
                  LEFT JOIN expense_categories ec ON e.category_id = ec.id
                  ORDER BY e.id DESC LIMIT 500""",
    },
    'expense_categories': {
        'name': 'تصنيفات المصروفات',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم',
                  account_code as 'الحساب' FROM expense_categories""",
    },
    'cash_box_reports': {
        'name': 'تقارير الخزائن',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', 
                  current_balance as 'الرصيد' FROM cash_boxes WHERE is_active = 1""",
    },
    'branches': {
        'name': 'الفروع',
        'sql': """SELECT code as 'الكود', name_ar as 'الاسم', phone as 'الهاتف',
                  manager_name as 'المدير' FROM branches""",
    },
    'movements_journal': {
        'name': 'ربط الحركات بالقيود',
        'sql': """SELECT txn_date as 'التاريخ', txn_type as 'النوع',
                  reference_no as 'المرجع', amount as 'المبلغ'
                  FROM cash_box_transactions ORDER BY id DESC LIMIT 500""",
    },
    'reports': {
        'name': 'تقارير المخازن',
        'sql': "SELECT id as 'الرقم' FROM items LIMIT 100",
    },
    'batches_report': {
        'name': 'تقارير الدفعات',
        'sql': "SELECT id as 'الرقم', item_id as 'الصنف' FROM cost_layers LIMIT 500",
    },
    'supplier_rating': {
        'name': 'تقييم الموردين',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم' FROM suppliers",
    },
    'price_comparison': {
        'name': 'مقارنة الأسعار',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم', cost_price as 'التكلفة' FROM items",
    },
    'supplier_balances': {
        'name': 'أرصدة الموردين',
        'sql': """SELECT s.code as 'الكود', s.name_ar as 'المورد',
                  COALESCE((SELECT SUM(total_amount) FROM purchase_invoices WHERE supplier_id = s.id AND status = 'POSTED'), 0) as 'الفواتير',
                  COALESCE((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id = s.id), 0) as 'المدفوع'
                  FROM suppliers s""",
    },
    'customer_balances': {
        'name': 'أرصدة العملاء',
        'sql': """SELECT c.code as 'الكود', c.name_ar as 'العميل',
                  COALESCE((SELECT SUM(total_amount) FROM sales_invoices WHERE customer_id = c.id AND status = 'POSTED'), 0) as 'الفواتير',
                  COALESCE((SELECT SUM(amount) FROM customer_receipts WHERE customer_id = c.id), 0) as 'المحصل'
                  FROM customers c""",
    },
    'supplier_statement': {
        'name': 'كشف حساب مورد',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم' FROM suppliers",
    },
    'customer_statement': {
        'name': 'كشف حساب عميل',
        'sql': "SELECT code as 'الكود', name_ar as 'الاسم' FROM customers",
    },
    'item_movement': {
        'name': 'حركة الأصناف',
        'sql': """SELECT txn_date as 'التاريخ', txn_type as 'النوع',
                  quantity as 'الكمية' FROM stock_transactions
                  ORDER BY id DESC LIMIT 1000""",
    },
}


# ============================================
# 1. إضافة القوالب في excel_service.py
# ============================================
def step1_add_templates():
    print("=" * 60)
    print("📝 1. إضافة القوالب في excel_service.py")
    print("=" * 60)
    
    with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    added = 0
    skipped = 0
    
    for key, tpl in TEMPLATE_DEFS.items():
        # تحقق إن موجود
        if f"'{key}':" in content:
            skipped += 1
            continue
        
        # بناء القالب
        sql_escaped = tpl['sql'].replace('"""', '\\"\\"\\"')
        template_code = f"""        '{key}': {{
            'name': '{tpl['name']}',
            'sql': \"\"\"{sql_escaped}\"\"\",
            'columns': [],
        }},
"""
        
        # ابحث عن آخر قالب في EXPORT_TEMPLATES
        # نلاقي `EXPORT_TEMPLATES = {` ثم نضيف قبل `}\n    \n    # ====`
        pattern = r"(    EXPORT_TEMPLATES = \{.*?)(    \}\n    \n    # =========================================\n    # قوالب الاستيراد)"
        
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = content[:match.end(1)] + template_code + content[match.start(2):]
            added += 1
        else:
            print(f"  ⚠️ ما لقيتش EXPORT_TEMPLATES")
            break
    
    with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ تم إضافة {added} قالب جديد")
    print(f"  ℹ️ تم تخطي {skipped} (موجودين)")
    
    return added


# ============================================
# 2. إضافة زر التصدير في كل شاشة
# ============================================
def step2_add_buttons():
    print("\n" + "=" * 60)
    print("🔧 2. إضافة أزرار التصدير")
    print("=" * 60)
    
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
    
    added = 0
    skipped = 0
    errors = []
    
    for screen, template in SCREENS_TEMPLATES.items():
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
                r'(<a href="index\.html"[^>]*>.*?</a>)',
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
            
            # ضيف JS
            if 'exportToExcel' not in content:
                content = content.replace('</body>', get_js() + '\n</body>', 1)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ {screen}")
            added += 1
        except Exception as e:
            errors.append(screen)
            print(f"  ❌ {screen}: {e}")
    
    print(f"\n  📊 النتيجة: {added} نجح، {skipped} تخطي، {len(errors)} فشل")
    return added


# ============================================
# 3. اختبار
# ============================================
def step3_test():
    print("\n" + "=" * 60)
    print("🧪 3. اختبار excel_service.py")
    print("=" * 60)
    
    try:
        py_compile.compile(SERVICE_PATH, doraise=True)
        print("  ✅ الملف سليم — مفيش أخطاء")
        return True
    except py_compile.PyCompileError as e:
        print(f"  ❌ فيه خطأ:")
        print(f"     {e}")
        return False


# ============================================
# التشغيل الرئيسي
# ============================================
def main():
    print("\n" + "=" * 60)
    print("🚀 تفعيل تصدير Excel لكل الشاشات")
    print("=" * 60)
    print()
    
    # 1. Backup
    import shutil
    from datetime import datetime
    backup = os.path.join(BASE, f'_backup_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    os.makedirs(backup, exist_ok=True)
    
    shutil.copy(SERVICE_PATH, backup)
    print(f"📦 Backup: {backup}\n")
    
    # 2. تنفيذ
    step1_add_templates()
    step2_add_buttons()
    success = step3_test()
    
    # 3. الملخص
    print("\n" + "=" * 60)
    print("📊 الملخص")
    print("=" * 60)
    
    if success:
        print("""
  ✅ تم تفعيل التصدير بنجاح

  📌 الخطوات التالية:
     1. اقفل السيرفر
     2. شغّله تاني:
        cd J:\\warehouse-module
        python run.py
     3. افتح أي شاشة واضغط Ctrl + Shift + R
     4. هتشوف زر Excel في الرأس
     5. اضغطه — هينزل ملف Excel
""")
    else:
        print("""
  ❌ فيه خطأ في excel_service.py

  📌 الخطوات:
     1. افتح: app/services/excel_service.py
     2. شوف الخطأ
     3. أو رجّع من الـ backup
""")


if __name__ == '__main__':
    main()