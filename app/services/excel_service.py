"""
خدمة استيراد/تصدير Excel — النسخة النهائية المصححة
- تدعم all aliases
- تدعم foreign keys (parent_code, default_uom_code, account_code, etc.)
- تتجاهل القيم الفاضية والوهمية (-)
- تتعامل مع الحقول الجديدة في item_groups
"""
import os
import io
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.database import db


# ============================================================
# قيم يجب تجاهلها عند الاستيراد
# ============================================================
IGNORE_VALUES = {'-', '', '0', 'None', 'none', 'null', 'NULL', 'nan', 'NaN'}


def is_empty(value):
    """التحقق من إن القيمة فاضية أو وهمية"""
    if value is None:
        return True
    s = str(value).strip()
    return s in IGNORE_VALUES


class ExcelService:
    """خدمة Excel الشاملة"""

    # =========================================
    # قوالب التصدير
    # =========================================
    EXPORT_TEMPLATES = {
        'accounts': {
            'name': 'الحسابات',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم عربي',
                       name_en as 'الاسم إنجليزي', level as 'المستوى',
                       nature as 'الطبيعة', parent_code as 'الحساب الأب',
                       financial_statement as 'القائمة',
                       CASE WHEN is_leaf = 1 THEN 'قابل للترحيل' ELSE 'تجميعي' END as 'النوع',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM accounts
                ORDER BY code
            """,
            'columns': ['الكود', 'الاسم عربي', 'الاسم إنجليزي', 'المستوى',
                       'الطبيعة', 'الحساب الأب', 'القائمة', 'النوع', 'الحالة'],
        },
        'customers': {
            'name': 'العملاء',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم', phone as 'الهاتف',
                       email as 'البريد', tax_number as 'الرقم الضريبي',
                       credit_limit as 'حد الائتمان', payment_terms as 'مدة السداد',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM customers
                ORDER BY code
            """,
            'columns': ['الكود', 'الاسم', 'الهاتف', 'البريد', 'الرقم الضريبي',
                       'حد الائتمان', 'مدة السداد', 'الحالة'],
        },
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
            'columns': ['الكود', 'الاسم', 'الهاتف', 'البريد', 'الرقم الضريبي',
                       'حد الائتمان', 'الحالة'],
        },
        'items': {
            'name': 'الأصناف',
            'sql': """
                SELECT i.code as 'الكود', 
                       i.name_ar as 'الاسم', 
                       i.name_en as 'الاسم إنجليزي',
                       COALESCE(i.barcode, '') as 'الباركود',
                       COALESCE(i.item_type, '') as 'النوع',
                       COALESCE(g.name_ar, '') as 'المجموعة',
                       COALESCE(i.reorder_level, 0) as 'حد الطلب'
                FROM items i
                LEFT JOIN item_groups g ON i.group_id = g.id
                ORDER BY i.code
            """,
            'columns': ['الكود', 'الاسم', 'الاسم إنجليزي', 'الباركود', 
                       'النوع', 'المجموعة', 'حد الطلب'],
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
            'columns': ['الكود', 'الاسم', 'الاسم إنجليزي', 'العنوان', 'الهاتف'],
        },
        'item_groups': {
            'name': 'مجموعات الأصناف',
            'sql': """
                SELECT g.code as 'الكود',
                       g.name_ar as 'الاسم بالعربي',
                       COALESCE(g.name_en, '') as 'الاسم بالإنجليزي',
                       COALESCE(p.code, '') as 'كود المجموعة الأب',
                       COALESCE(u.code, '') as 'كود الوحدة',
                       COALESCE(g.inventory_account, '') as 'حساب المخزون',
                       COALESCE(g.cost_account, '') as 'حساب التكلفة',
                       COALESCE(g.revenue_account, '') as 'حساب الإيراد',
                       COALESCE(g.purchase_account, '') as 'حساب المشتريات',
                       COALESCE(g.adjustment_account, '') as 'حساب التسوية',
                       COALESCE(g.waste_account, '') as 'حساب الهالك',
                       COALESCE(g.clearing_account, '') as 'حساب الوسيط',
                       COALESCE(g.revenue_return_account, '') as 'مردودات الإيراد',
                       COALESCE(g.discount_account, '') as 'الخصم المسموح',
                       COALESCE(g.default_cost_method, 'WEIGHTED_AVERAGE') as 'طريقة التكلفة',
                       COALESCE(g.notes, '') as 'ملاحظات',
                       CASE WHEN g.is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM item_groups g
                LEFT JOIN item_groups p ON g.parent_id = p.id   
                LEFT JOIN units_of_measure u ON g.default_uom_id = u.id
                ORDER BY g.code
            """,
            'columns': [
                'الكود', 'الاسم بالعربي', 'الاسم بالإنجليزي',
                'كود المجموعة الأب', 'كود الوحدة',
                'حساب المخزون', 'حساب التكلفة', 'حساب الإيراد',
                'حساب المشتريات', 'حساب التسوية', 'حساب الهالك',
                'حساب الوسيط', 'مردودات الإيراد', 'الخصم المسموح',
                'طريقة التكلفة', 'ملاحظات', 'الحالة'
            ],
        },
        'uom': {
            'name': 'وحدات القياس',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم',
                       COALESCE(name_en, '') as 'الاسم إنجليزي'
                FROM units_of_measure
                ORDER BY code
            """,
            'columns': ['الكود', 'الاسم', 'الاسم إنجليزي'],
        },
        'cash_boxes': {
            'name': 'الخزائن',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم',
                       box_type as 'النوع', account_code as 'الحساب',
                       opening_balance as 'الرصيد الافتتاحي',
                       current_balance as 'الرصيد الحالي',
                       currency as 'العملة'
                FROM cash_boxes
                WHERE is_active = 1
                ORDER BY code
            """,
            'columns': ['الكود', 'الاسم', 'النوع', 'الحساب',
                       'الرصيد الافتتاحي', 'الرصيد الحالي', 'العملة'],
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
            'columns': ['الكود', 'الاسم', 'الحساب', 'رقم الحساب', 'IBAN',
                       'SWIFT', 'الفرع', 'الرصيد'],
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
            'columns': ['الكود', 'الاسم', 'الهاتف', 'المدير', 'العنوان', 'الحالة'],
        },
        'journal_entries': {
            'name': 'القيود',
            'sql': """
                SELECT je.entry_no as 'رقم القيد', je.entry_date as 'التاريخ',
                       COALESCE(je.reference_type, '') as 'نوع المرجع',
                       COALESCE(je.reference_no, '') as 'رقم المرجع',
                       COALESCE(je.description, '') as 'البيان',
                       je.total_debit as 'إجمالي مدين', 
                       je.total_credit as 'إجمالي دائن',
                       je.status as 'الحالة'
                FROM journal_entries je
                ORDER BY je.entry_date DESC, je.id DESC
                LIMIT 1000
            """,
            'columns': ['رقم القيد', 'التاريخ', 'نوع المرجع', 'رقم المرجع',
                       'البيان', 'إجمالي مدين', 'إجمالي دائن', 'الحالة'],
        },
        'supplier_payments': {
            'name': 'مدفوعات الموردين',
            'sql': """
                SELECT sp.payment_no as 'رقم الدفعة', sp.payment_date as 'التاريخ',
                       COALESCE(s.name_ar, '') as 'المورد',
                       sp.payment_method as 'طريقة السداد',
                       sp.amount as 'المبلغ', 
                       COALESCE(sp.reference, '') as 'المرجع',
                       COALESCE(je.entry_no, '') as 'رقم القيد'
                FROM supplier_payments sp
                LEFT JOIN suppliers s ON sp.supplier_id = s.id
                LEFT JOIN journal_entries je ON sp.journal_entry_id = je.id
                ORDER BY sp.id DESC
                LIMIT 500
            """,
            'columns': ['رقم الدفعة', 'التاريخ', 'المورد', 'طريقة السداد',
                       'المبلغ', 'المرجع', 'رقم القيد'],
        },
        'customer_receipts': {
            'name': 'تحصيلات العملاء',
            'sql': """
                SELECT cr.receipt_no as 'رقم التحصيل', cr.receipt_date as 'التاريخ',
                       COALESCE(c.name_ar, '') as 'العميل',
                       cr.receipt_method as 'طريقة التحصيل',
                       cr.amount as 'المبلغ',
                       COALESCE(cr.reference, '') as 'المرجع',
                       COALESCE(je.entry_no, '') as 'رقم القيد'
                FROM customer_receipts cr
                LEFT JOIN customers c ON cr.customer_id = c.id
                LEFT JOIN journal_entries je ON cr.journal_entry_id = je.id
                ORDER BY cr.id DESC
                LIMIT 500
            """,
            'columns': ['رقم التحصيل', 'التاريخ', 'العميل', 'طريقة التحصيل',
                       'المبلغ', 'المرجع', 'رقم القيد'],
        },
        'cash_box_transactions': {
            'name': 'حركات الخزائن',
            'sql': """
                SELECT cbt.txn_date as 'التاريخ', cbt.txn_type as 'النوع',
                       COALESCE(cbt.reference_no, '') as 'المرجع',
                       COALESCE(cb.name_ar, b.name_ar, pc.name_ar, '') as 'الخزينة',
                       cbt.amount as 'المبلغ',
                       COALESCE(cbt.balance_after, 0) as 'الرصيد بعد',
                       COALESCE(cbt.description, '') as 'البيان'
                FROM cash_box_transactions cbt
                LEFT JOIN cash_boxes cb ON cbt.box_type = 'CASH_BOX' AND cbt.box_id = cb.id
                LEFT JOIN banks b ON cbt.box_type = 'BANK' AND cbt.box_id = b.id
                LEFT JOIN payment_cards pc ON cbt.box_type = 'CARD' AND cbt.box_id = pc.id
                ORDER BY cbt.txn_date DESC, cbt.id DESC
                LIMIT 500
            """,
            'columns': ['التاريخ', 'النوع', 'المرجع', 'الخزينة',
                       'المبلغ', 'الرصيد بعد', 'البيان'],
        },
        'expenses': {
            'name': 'المصروفات',
            'sql': """
                SELECT e.expense_no as 'رقم المصروف', e.expense_date as 'التاريخ',
                       COALESCE(ec.name_ar, '') as 'التصنيف',
                       COALESCE(e.beneficiary, '') as 'المستفيد',
                       COALESCE(cb.name_ar, '') as 'الخزينة',
                       e.amount as 'المبلغ',
                       COALESCE(e.description, '') as 'البيان',
                       COALESCE(e.reference, '') as 'المرجع'
                FROM petty_cash_expenses e
                LEFT JOIN expense_categories ec ON e.category_id = ec.id
                LEFT JOIN cash_boxes cb ON e.cash_box_id = cb.id
                ORDER BY e.expense_date DESC, e.id DESC
                LIMIT 500
            """,
            'columns': ['رقم المصروف', 'التاريخ', 'التصنيف', 'المستفيد',
                       'الخزينة', 'المبلغ', 'البيان', 'المرجع'],
        },
        'expense_categories': {
            'name': 'تصنيفات المصروفات',
            'sql': """
                SELECT ec.code as 'الكود', ec.name_ar as 'الاسم',
                       ec.account_code as 'الحساب',
                       COALESCE(a.name_ar, '') as 'اسم الحساب',
                       CASE WHEN ec.is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM expense_categories ec
                LEFT JOIN accounts a ON ec.account_code = a.code
                ORDER BY ec.code
            """,
            'columns': ['الكود', 'الاسم', 'الحساب', 'اسم الحساب', 'الحالة'],
        },
        'purchase_invoices': {
            'name': 'فواتير الشراء',
            'sql': """
                SELECT pi.invoice_no as 'رقم الفاتورة', pi.invoice_date as 'التاريخ',
                       COALESCE(s.name_ar, '') as 'المورد',
                       COALESCE(w.name_ar, '') as 'المستودع',
                       pi.total_amount as 'الإجمالي',
                       COALESCE(pi.payment_type, '') as 'نوع الدفع',
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
                       COALESCE(c.name_ar, '') as 'العميل',
                       COALESCE(w.name_ar, '') as 'المستودع',
                       si.total_amount as 'الإجمالي',
                       COALESCE(si.payment_type, '') as 'نوع الدفع',
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
            'columns': ['رقم المرتجع', 'التاريخ', 'المورد', 'الإجمالي', 'الحالة'],
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
            'columns': ['رقم المرتجع', 'التاريخ', 'العميل', 'الإجمالي', 'الحالة'],
        },
        'stock_transactions': {
            'name': 'حركات المخزون',
            'sql': """
                SELECT st.transaction_date as 'التاريخ', 
                       st.transaction_type as 'النوع',
                       COALESCE(st.reference_no, '') as 'المرجع',
                       COALESCE(st.notes, '') as 'البيان',
                       COALESCE(st.total_qty, 0) as 'إجمالي الكمية',
                       COALESCE(st.total_value, 0) as 'إجمالي القيمة',
                       st.status as 'الحالة'
                FROM stock_transactions st
                ORDER BY st.transaction_date DESC, st.id DESC
                LIMIT 1000
            """,
            'columns': ['التاريخ', 'النوع', 'المرجع', 'البيان',
                       'إجمالي الكمية', 'إجمالي القيمة', 'الحالة'],
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
            'columns': ['رقم الجرد', 'التاريخ', 'المستودع', 'النوع', 'الحالة', 'رقم القيد'],
        },
        'payment_methods': {
            'name': 'طرق الدفع',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم', 
                       account_code as 'الحساب',
                       CASE WHEN requires_clearing = 1 THEN 'يحتاج تسوية' ELSE 'مباشر' END as 'النوع',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM payment_methods
                ORDER BY id
            """,
            'columns': ['الكود', 'الاسم', 'الحساب', 'النوع', 'الحالة'],
        },
        'tax_settings': {
            'name': 'الضرائب',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم', 
                       tax_type as 'النوع', rate as 'النسبة',
                       account_code as 'الحساب',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM tax_settings
                ORDER BY id
            """,
            'columns': ['الكود', 'الاسم', 'النوع', 'النسبة', 'الحساب', 'الحالة'],
        },
        'discount_settings': {
            'name': 'الخصومات',
            'sql': """
                SELECT code as 'الكود', name_ar as 'الاسم',
                       discount_type as 'النوع', default_rate as 'النسبة',
                       account_code as 'الحساب',
                       CASE WHEN is_active = 1 THEN 'نشط' ELSE 'موقوف' END as 'الحالة'
                FROM discount_settings
                ORDER BY id
            """,
            'columns': ['الكود', 'الاسم', 'النوع', 'النسبة', 'الحساب', 'الحالة'],
        },
        'supplier_balances': {
            'name': 'أرصدة الموردين',
            'sql': """
                SELECT s.code as 'الكود', s.name_ar as 'المورد',
                       COALESCE((SELECT SUM(total_amount) FROM purchase_invoices WHERE supplier_id = s.id AND status = 'POSTED'), 0) as 'الفواتير',
                       COALESCE((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id = s.id), 0) as 'المدفوع',
                       COALESCE((SELECT SUM(total_amount) FROM purchase_invoices WHERE supplier_id = s.id AND status = 'POSTED'), 0) - 
                       COALESCE((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id = s.id), 0) as 'الرصيد'
                FROM suppliers s
                ORDER BY s.code
            """,
            'columns': ['الكود', 'المورد', 'الفواتير', 'المدفوع', 'الرصيد'],
        },
        'customer_balances': {
            'name': 'أرصدة العملاء',
            'sql': """
                SELECT c.code as 'الكود', c.name_ar as 'العميل',
                       COALESCE((SELECT SUM(total_amount) FROM sales_invoices WHERE customer_id = c.id AND status = 'POSTED'), 0) as 'الفواتير',
                       COALESCE((SELECT SUM(amount) FROM customer_receipts WHERE customer_id = c.id), 0) as 'المحصل',
                       COALESCE((SELECT SUM(total_amount) FROM sales_invoices WHERE customer_id = c.id AND status = 'POSTED'), 0) - 
                       COALESCE((SELECT SUM(amount) FROM customer_receipts WHERE customer_id = c.id), 0) as 'الرصيد'
                FROM customers c
                ORDER BY c.code
            """,
            'columns': ['الكود', 'العميل', 'الفواتير', 'المحصل', 'الرصيد'],
        },
    }

    # =========================================
    # قوالب الاستيراد
    # =========================================
    IMPORT_TEMPLATES = {
        'accounts': {
            'name': 'الحسابات',
            'table': 'accounts',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم عربي',
                'name_en': 'الاسم إنجليزي',
                'level': 'المستوى',
                'nature': 'الطبيعة',
                'parent_code': 'الحساب الأب',
                'financial_statement': 'القائمة',
            },
            'required': ['code', 'name_ar'],
            'aliases': {
                'name_ar': ['الاسم', 'الاسم العربي', 'الاسم بالعربي', 'name_ar'],
                'name_en': ['الاسم إنجليزي', 'الاسم الإنجليزي', 'name_en'],
                'parent_code': ['الأب', 'الحساب الاب', 'parent', 'parent_code'],
            },
        },
        'customers': {
            'name': 'العملاء',
            'table': 'customers',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'phone': 'الهاتف',
                'email': 'البريد',
                'tax_number': 'الرقم الضريبي',
                'credit_limit': 'حد الائتمان',
                'payment_terms': 'مدة السداد',
            },
            'required': ['code', 'name_ar'],
        },
        'suppliers': {
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
        },
        'items': {
            'name': 'الأصناف',
            'table': 'items',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم',
                'name_en': 'الاسم إنجليزي',
                'barcode': 'الباركود',
                'item_type': 'النوع',
                'reorder_level': 'حد الطلب',
            },
            'required': ['code', 'name_ar'],
        },
        'warehouses': {
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
        },
        'item_groups': {
            'name': 'مجموعات الأصناف',
            'table': 'item_groups',
            'columns': {
                'code': 'الكود',
                'name_ar': 'الاسم بالعربي',
                'name_en': 'الاسم بالإنجليزي',
                'parent_code': 'كود المجموعة الأب',
                'default_uom_code': 'كود الوحدة',
                'inventory_account': 'حساب المخزون',
                'cost_account': 'حساب التكلفة',
                'revenue_account': 'حساب الإيراد',
                'purchase_account': 'حساب المشتريات',
                'adjustment_account': 'حساب التسوية',
                'waste_account': 'حساب الهالك',
                'clearing_account': 'حساب الوسيط',
                'revenue_return_account': 'مردودات الإيراد',
                'discount_account': 'الخصم المسموح',
                'default_cost_method': 'طريقة التكلفة',
                'notes': 'ملاحظات',
            },
            'required': ['code', 'name_ar'],
            'aliases': {
                'code': ['كود', 'code'],
                'name_ar': ['الاسم', 'الاسم عربي', 'الاسم العربي', 'name_ar'],
                'name_en': ['الاسم إنجليزي', 'الاسم الإنجليزي', 'الاسم انجليزي', 'name_en'],
                'parent_code': ['الأب', 'المجموعة الأب', 'كود المجموعة الاب', 'parent', 'parent_code'],
                'default_uom_code': ['الوحدة', 'الوحدة الافتراضية', 'كود الوحده', 'uom', 'unit'],
                'inventory_account': ['المخزون', 'inventory', 'inventory_account'],
                'cost_account': ['التكلفة', 'cost', 'cost_account'],
                'revenue_account': ['الإيراد', 'revenue', 'revenue_account'],
                'purchase_account': ['المشتريات', 'purchase', 'purchase_account'],
                'adjustment_account': ['التسوية', 'adjustment', 'adjustment_account'],
                'waste_account': ['الهالك', 'waste', 'waste_account'],
                'clearing_account': ['الوسيط', 'clearing', 'clearing_account'],
                'revenue_return_account': ['مردودات', 'revenue_return', 'revenue_return_account'],
                'discount_account': ['الخصم', 'discount', 'discount_account'],
                'default_cost_method': ['طريقة التكلفه', 'cost_method', 'default_cost_method'],
                'notes': ['ملاحظة', 'notes'],
            },
            'foreign_keys': {
                'parent_code': {'table': 'item_groups', 'column': 'code', 'target': 'parent_id'},
                'default_uom_code': {'table': 'units_of_measure', 'column': 'code', 'target': 'default_uom_id'},
            },
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
            'foreign_keys': {
                'account_code': {'table': 'accounts', 'column': 'code', 'target': 'account_code'},
            },
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
                'currency': 'العملة',
            },
            'required': ['code', 'name_ar', 'account_code'],
            'foreign_keys': {
                'account_code': {'table': 'accounts', 'column': 'code', 'target': 'account_code'},
            },
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
            'foreign_keys': {
                'account_code': {'table': 'accounts', 'column': 'code', 'target': 'account_code'},
            },
        },
    }

    # =========================================
    # التصدير
    # =========================================

    def export_to_excel(self, template_key, filters=None):
        """تصدير بيانات لـ Excel — حتى لو مفيش بيانات"""
        if template_key not in self.EXPORT_TEMPLATES:
            return None, 'قالب غير موجود'

        template = self.EXPORT_TEMPLATES[template_key]
        sql = template['sql']

        # جلب البيانات
        try:
            rows = db.query(sql)
        except Exception as e:
            return None, str(e)

        # إنشاء Excel
        wb = Workbook()
        ws = wb.active
        ws.title = template['name'][:31]  # Excel limit
        ws.sheet_view.rightToLeft = True

        # الألوان
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True, size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # الحصول على أسماء الأعمدة
        if rows and len(rows) > 0:
            columns = list(rows[0].keys())
        else:
            try:
                test_sql = f"SELECT * FROM ({sql}) LIMIT 0"
                test_rows = db.query(test_sql)
                if test_rows and len(test_rows) > 0:
                    columns = list(test_rows[0].keys())
                else:
                    columns = template.get('columns', ['لا توجد بيانات'])
            except:
                columns = template.get('columns', ['لا توجد بيانات'])

        # العناوين
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # البيانات
        if rows and len(rows) > 0:
            for row_idx, row in enumerate(rows, 2):
                for col_idx, col_name in enumerate(columns, 1):
                    value = row.get(col_name)
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border
                    cell.alignment = Alignment(horizontal='right', vertical='center')
        else:
            cell = ws.cell(row=2, column=1, value='لا توجد بيانات')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.font = Font(italic=True, color='808080')

        # عرض الأعمدة
        for col_idx, col_name in enumerate(columns, 1):
            max_length = len(str(col_name))
            if rows and len(rows) > 0:
                for row in rows[:100]:
                    val = str(row.get(col_name, ''))
                    if len(val) > max_length:
                        max_length = len(val)
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_length + 4, 12), 50)

        # حفظ
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output, None

    # =========================================
    # الاستيراد
    # =========================================

    def import_from_excel(self, template_key, file_content, dry_run=False):
        """استيراد من Excel — يدعم foreign keys و aliases ويتجاهل القيم الفاضية"""
        if template_key not in self.IMPORT_TEMPLATES:
            return {'success': False, 'message': 'قالب غير موجود'}

        template = self.IMPORT_TEMPLATES[template_key]

        try:
            wb = load_workbook(io.BytesIO(file_content), data_only=True)
            ws = wb.active
        except Exception as e:
            return {'success': False, 'message': f'ملف Excel غير صالح: {e}'}

        # قراءة العناوين
        headers = []
        for col in ws[1]:
            headers.append(str(col.value).strip() if col.value else '')

        # خريطة الأعمدة (بندعم * + aliases)
        col_map = {}
        aliases = template.get('aliases', {})

        for field, label in template['columns'].items():
            # الأسماء المحتملة = الليبل الرسمي + aliases
            possible_names = [label] + aliases.get(field, [])
            # نظف الأسماء من *
            possible_names = [n.replace(' *', '').replace('*', '').strip() for n in possible_names]

            for idx, h in enumerate(headers):
                h_clean = h.replace(' *', '').replace('*', '').strip()
                if h_clean in possible_names:
                    col_map[field] = idx
                    break

        # التحقق من المطلوب
        missing = []
        for field in template['required']:
            if field not in col_map:
                missing.append(template['columns'].get(field, field))

        if missing:
            return {
                'success': False,
                'message': f'أعمدة مطلوبة ناقصة: {", ".join(missing)}'
            }

        # قراءة الصفوف
        imported = 0
        updated = 0
        skipped = 0
        errors = []
        preview = []
        valid_rows = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):
                continue

            data = {}
            for field, col_idx in col_map.items():
                value = row[col_idx] if col_idx < len(row) else None
                # تنظيف القيم النصية
                if isinstance(value, str):
                    value = value.strip()
                    if value == '':
                        value = None
                data[field] = value

            # التحقق من المطلوب (نتجاهل القيم الوهمية)
            required_ok = True
            for f in template['required']:
                v = data.get(f)
                if is_empty(v):
                    required_ok = False
                    break

            if not required_ok:
                skipped += 1
                continue

            valid_rows.append((row_idx, data))

            if dry_run and len(preview) < 10:
                preview.append({
                    'row': row_idx,
                    'data': {k: (str(v)[:30] if v is not None else '-') for k, v in data.items()}
                })

        if dry_run:
            return {
                'success': True,
                'data': {
                    'dry_run': True,
                    'total_rows': len(valid_rows),
                    'preview': preview,
                    'errors': errors[:20]
                }
            }

        table = template['table']

        table_exists = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,), one=True
        )

        if not table_exists:
            return {
                'success': False,
                'message': f'الجدول {table} مش موجود'
            }

        # معالجة foreign keys
        foreign_keys = template.get('foreign_keys', {})

        for row_idx, data in valid_rows:
            try:
                # تحويل foreign keys
                fk_values = {}
                skip_row = False

                for fk_field, fk_config in foreign_keys.items():
                    if fk_field in data:
                        ref_value = data.pop(fk_field)

                        # تجاهل القيم الفاضية أو الوهمية
                        if is_empty(ref_value):
                            continue

                        ref_row = db.query(
                            f"SELECT id FROM {fk_config['table']} WHERE {fk_config['column']} = ?",
                            (ref_value,), one=True
                        )
                        if ref_row:
                            fk_values[fk_config['target']] = ref_row['id']
                        else:
                            # لو مش موجود، نتجاهله بدل ما نوقف الصف
                            errors.append(f'صف {row_idx}: {fk_field}={ref_value} غير موجود — تم تجاهله')

                # دمج foreign keys
                data.update(fk_values)

                # التحقق من وجود السجل
                if 'code' in data and data['code']:
                    existing = db.query(
                        f"SELECT id FROM {table} WHERE code = ?",
                        (data['code'],), one=True
                    )
                else:
                    existing = None

                if existing:
                    fields = [f"{k} = ?" for k in data.keys() if k != 'code']
                    values = [data[k] for k in data.keys() if k != 'code']
                    values.append(data['code'])
                    db.execute(
                        f"UPDATE {table} SET {', '.join(fields)} WHERE code = ?",
                        values
                    )
                    updated += 1
                else:
                    cols = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data])
                    values = list(data.values())
                    db.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                        values
                    )
                    imported += 1
            except Exception as e:
                errors.append(f'صف {row_idx}: {str(e)[:80]}')

        return {
            'success': True,
            'data': {
                'imported': imported,
                'updated': updated,
                'skipped': skipped,
                'total': imported + updated,
                'errors': errors[:20]
            }
        }

    # =========================================
    # قالب الاستيراد الفارغ
    # =========================================

    def get_import_template(self, template_key):
        """إنشاء ملف Excel فاضي للاستيراد"""
        if template_key not in self.IMPORT_TEMPLATES:
            return None

        template = self.IMPORT_TEMPLATES[template_key]

        wb = Workbook()
        ws = wb.active
        ws.title = template['name']
        ws.sheet_view.rightToLeft = True

        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        required_fill = PatternFill(start_color='C00000', end_color='C00000', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True, size=12)

        for col_idx, (field, label) in enumerate(template['columns'].items(), 1):
            cell = ws.cell(row=1, column=col_idx, value=label)
            if field in template['required']:
                cell.fill = required_fill
                cell.value = f"{label} *"
            else:
                cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.column_dimensions[get_column_letter(col_idx)].width = 20

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output

    # =========================================
    # قائمة القوالب
    # =========================================

    def list_templates(self):
        """قائمة القوالب"""
        return {
            'export': [
                {'key': k, 'name': v['name']}
                for k, v in self.EXPORT_TEMPLATES.items()
            ],
            'import': [
                {'key': k, 'name': v['name']}
                for k, v in self.IMPORT_TEMPLATES.items()
            ]
        }


excel_service = ExcelService()