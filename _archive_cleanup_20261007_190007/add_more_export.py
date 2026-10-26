"""
إضافة المزيد من قوالب التصدير + الأزرار
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================
# 1. إضافة قوالب في excel_service.py
# ============================================
print("=" * 60)
print("📝 1. إضافة قوالب Excel")
print("=" * 60)

service_path = os.path.join(BASE, 'app', 'services', 'excel_service.py')

with open(service_path, 'r', encoding='utf-8') as f:
    content = f.read()

# القوالب الجديدة
new_templates = '''        'purchase_invoices': {
            'name': 'فواتير الشراء',
            'sql': """
                SELECT pi.invoice_no as 'رقم الفاتورة', pi.invoice_date as 'التاريخ',
                       s.name_ar as 'المورد', w.name_ar as 'المستودع',
                       pi.total_amount as 'الإجمالي', pi.payment_type as 'نوع الدفع',
                       pi.status as 'الحالة'
                FROM purchase_invoices pi
                LEFT JOIN suppliers s ON pi.supplier_id = s.id
                LEFT JOIN warehouses w ON pi.warehouse_id = w.id
                ORDER BY pi.invoice_date DESC, pi.id DESC
                LIMIT 1000
            """,
            'columns': ['رقم الفاتورة', 'التاريخ', 'المورد', 'المستودع', 
                       'الإجمالي', 'نوع الدفع', 'الحالة'],
        },
        'sales_invoices': {
            'name': 'فواتير البيع',
            'sql': """
                SELECT si.invoice_no as 'رقم الفاتورة', si.invoice_date as 'التاريخ',
                       c.name_ar as 'العميل', w.name_ar as 'المستودع',
                       si.total_amount as 'الإجمالي', si.payment_type as 'نوع الدفع',
                       si.status as 'الحالة'
                FROM sales_invoices si
                LEFT JOIN customers c ON si.customer_id = c.id
                LEFT JOIN warehouses w ON si.warehouse_id = w.id
                ORDER BY si.invoice_date DESC, si.id DESC
                LIMIT 1000
            """,
            'columns': ['رقم الفاتورة', 'التاريخ', 'العميل', 'المستودع', 
                       'الإجمالي', 'نوع الدفع', 'الحالة'],
        },
        'purchase_returns': {
            'name': 'مرتجع شراء',
            'sql': """
                SELECT pr.return_no as 'رقم المرتجع', pr.return_date as 'التاريخ',
                       s.name_ar as 'المورد', pr.total_amount as 'الإجمالي',
                       pr.status as 'الحالة'
                FROM purchase_returns pr
                LEFT JOIN suppliers s ON pr.supplier_id = s.id
                ORDER BY pr.return_date DESC, pr.id DESC
                LIMIT 500
            """,
            'columns': ['رقم المرتجع', 'التاريخ', 'المورد', 'الإجمالي', 'الحالة'],
        },
        'sales_returns': {
            'name': 'مرتجع بيع',
            'sql': """
                SELECT sr.return_no as 'رقم المرتجع', sr.return_date as 'التاريخ',
                       c.name_ar as 'العميل', sr.total_amount as 'الإجمالي',
                       sr.status as 'الحالة'
                FROM sales_returns sr
                LEFT JOIN customers c ON sr.customer_id = c.id
                ORDER BY sr.return_date DESC, sr.id DESC
                LIMIT 500
            """,
            'columns': ['رقم المرتجع', 'التاريخ', 'العميل', 'الإجمالي', 'الحالة'],
        },
        'branches': {
            'name': 'الفروع',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم', phone as 'الهاتف',
                       manager_name as 'المدير', address as 'العنوان',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM branches
                ORDER BY code
            """,
            'columns': ['الكود', 'الاسم', 'الهاتف', 'المدير', 'العنوان', 'الحالة'],
        },
        'expense_categories': {
            'name': 'تصنيفات المصروفات',
            'sql': """
                SELECT ec.code as 'الكود', ec.name_ar as 'الاسم',
                       ec.account_code as 'الحساب', a.name_ar as 'اسم الحساب',
                       CASE WHEN ec.is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM expense_categories ec
                LEFT JOIN accounts a ON ec.account_code = a.code
                ORDER BY ec.code
            """,
            'columns': ['الكود', 'الاسم', 'الحساب', 'اسم الحساب', 'الحالة'],
        },
        'stock_transactions': {
            'name': 'حركات المخزون',
            'sql': """
                SELECT st.txn_date as 'التاريخ', st.txn_type as 'النوع',
                       st.reference_no as 'المرجع',
                       i.name_ar as 'الصنف', w.name_ar as 'المستودع',
                       st.quantity as 'الكمية'
                FROM stock_transactions st
                LEFT JOIN items i ON st.item_id = i.id
                LEFT JOIN warehouses w ON st.warehouse_id = w.id
                ORDER BY st.txn_date DESC, st.id DESC
                LIMIT 1000
            """,
            'columns': ['التاريخ', 'النوع', 'المرجع', 'الصنف', 'المستودع', 'الكمية'],
        },
        'payment_allocations': {
            'name': 'توزيعات المدفوعات',
            'sql': """
                SELECT pa.payment_type as 'النوع', pa.invoice_type as 'نوع الفاتورة',
                       pa.invoice_no as 'رقم الفاتورة', pa.amount as 'المبلغ'
                FROM payment_allocations pa
                ORDER BY pa.id DESC
                LIMIT 1000
            """,
            'columns': ['النوع', 'نوع الفاتورة', 'رقم الفاتورة', 'المبلغ'],
        },
    }
}'''

# استبدل القوس الأخير
old_end = """        },
    }
    
    # =========================================
    # قوالب الاستيراد
    # ========================================="""

if old_end in content:
    # ابحث عن آخر قالب في EXPORT_TEMPLATES
    # نلاقي `'columns': [...]},\n    }\n    \n    # =====...قوالب الاستيراد`
    pattern = r"(        \'cash_box_transactions\': \{.*?\n        \},\n        \'expenses\': \{.*?\n        \},\n)(    \}\n    \n    # =========================================\n    # قوالب الاستيراد)"
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        # ضيف القوالب الجديدة قبل القوس الأخير
        # نشيل القوس `}` الأخير من new_templates عشان نستخدم old
        extra = new_templates.rsplit('    }', 1)[0]
        
        # استبدل
        content = content[:match.end(1)] + extra + content[match.start(2):]
        
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("  ✅ تم إضافة 8 قوالب جديدة")
    else:
        print("  ⚠️ ما لقيتش نهاية EXPORT_TEMPLATES")
else:
    print("  ⚠️ النمط مش موجود")


# ============================================
# 2. إضافة الأزرار في الشاشات
# ============================================
print("\n" + "=" * 60)
print("🔧 2. إضافة أزرار جديدة")
print("=" * 60)

STATIC = os.path.join(BASE, 'app', 'static')

NEW_SCREENS = {
    'purchase_invoices.html': 'purchase_invoices',
    'sales_invoices.html': 'sales_invoices',
    'purchase_returns.html': 'purchase_returns',
    'sales_returns.html': 'sales_returns',
    'branches.html': 'branches',
    'expense_categories.html': 'expense_categories',
}

def get_export_button(template_key):
    return f'''<button class="btn btn-sm btn-outline-success" onclick="exportToExcel('{template_key}')" title="تصدير Excel">
                <i class="bi bi-file-earmark-excel"></i> Excel
            </button>'''

def get_export_js():
    return '''
<script>
function exportToExcel(templateKey) {
    if (!templateKey) return;
    window.location.href = `/api/v1/export/excel/export/${templateKey}`;
}
</script>
'''

total = 0
for screen, template in NEW_SCREENS.items():
    path = os.path.join(STATIC, screen)
    
    if not os.path.exists(path):
        print(f"  ⏭️ {screen}: مش موجود")
        continue
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'exportToExcel' in content:
            print(f"  ℹ️ {screen}: الزر موجود")
            continue
        
        # ابحث عن زر "الرئيسية" وضيف قبله
        patterns_alt = [
            r'(<a href="index\.html" class="btn[^"]*"[^>]*>\s*<i class="bi bi-house[^>]*></i>\s*الرئيسية\s*</a>)',
            r'(<a href="index\.html"[^>]*>.*?الرئيسية.*?</a>)',
        ]
        
        button_added = False
        for pattern in patterns_alt:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insert_pos = match.start()
                button_html = get_export_button(template) + '\n            '
                content = content[:insert_pos] + button_html + content[insert_pos:]
                button_added = True
                break
        
        if not button_added:
            print(f"  ⚠️ {screen}: مفيش مكان")
            continue
        
        if 'exportToExcel' not in content:
            content = content.replace('</body>', get_export_js() + '\n</body>', 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ {screen}: تم إضافة الزر")
        total += 1
    except Exception as e:
        print(f"  ❌ {screen}: {e}")

print(f"\n  ✅ إجمالي: {total}")