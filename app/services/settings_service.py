"""خدمة الإعدادات - قراءة مركزية لكل الإعدادات مع Cache"""
from app.database import db
from datetime import datetime

# Cache للإعدادات
_cache = {}


def get_settings(category):
    """جلب كل إعدادات فئة معينة (مع cache)"""
    if category in _cache:
        return _cache[category]

    rows = db.query(
        "SELECT key, value, value_type FROM settings WHERE category=?",
        (category,)
    )
    result = {}
    for r in rows:
        val = r['value']
        vtype = r['value_type'] or 'string'
        if vtype == 'bool':
            val = val in ('1', 'true', 'True')
        elif vtype == 'int':
            try:
                val = int(val) if val not in (None, '') else 0
            except:
                val = 0
        elif vtype == 'float':
            try:
                val = float(val) if val not in (None, '') else 0.0
            except:
                val = 0.0
        result[r['key']] = val

    _cache[category] = result
    return result


def get_setting(category, key, default=None):
    """جلب إعداد واحد"""
    s = get_settings(category)
    return s.get(key, default)


def clear_cache(category=None):
    """مسح cache - يُستدعى بعد تحديث الإعدادات"""
    global _cache
    if category:
        _cache.pop(category, None)
    else:
        _cache = {}


# ==========================================
# Helpers لكل فئة
# ==========================================
def get_company():
    return get_settings('company')


def get_customers():
    return get_settings('customers')


def get_suppliers():
    return get_settings('suppliers')


def get_accounting():
    return get_settings('accounting')


def get_inventory():
    return get_settings('inventory')


def get_cash():
    return get_settings('cash')


def get_print():
    return get_settings('print')


def get_backup():
    return get_settings('backup')


# ==========================================
# Helper: رصيد العميل
# ==========================================
def get_customer_balance(customer_id):
    """جلب رصيد العميل الحالي (مدين - دائن)"""
    row = db.query(
        """SELECT
             COALESCE((
                SELECT SUM(si.total_amount)
                FROM sales_invoices si
                WHERE si.customer_id = ? AND si.status = 'POSTED'
             ), 0) AS total_invoiced,
             COALESCE((
                SELECT SUM(cr.amount)
                FROM customer_receipts cr
                WHERE cr.customer_id = ?
             ), 0) AS total_paid""",
        (customer_id, customer_id),
        one=True
    )
    invoiced = float(row['total_invoiced'] or 0) if row else 0
    paid = float(row['total_paid'] or 0) if row else 0
    return {
        'invoiced': invoiced,
        'paid': paid,
        'balance': invoiced - paid
    }


# ==========================================
# Helper: عدد الفواتير المتأخرة للعميل
# ==========================================
def get_overdue_invoices_count(customer_id, payment_terms=None):
    """
    عدد الفواتير المتأخرة للعميل
    payment_terms: مدة السماح بالأيام
    """
    if payment_terms is None:
        # من إعدادات العميل، أو من settings
        cust = db.query(
            "SELECT payment_terms FROM customers WHERE id=?",
            (customer_id,), one=True
        )
        if cust and cust['payment_terms']:
            payment_terms = int(cust['payment_terms'])
        else:
            payment_terms = int(get_setting('customers', 'default_payment_terms', 30))

    row = db.query(
        """SELECT COUNT(*) AS cnt
           FROM sales_invoices
           WHERE customer_id = ?
             AND status = 'POSTED'
             AND julianday('now') - julianday(invoice_date) > ?""",
        (customer_id, payment_terms),
        one=True
    )
    return int(row['cnt'] or 0) if row else 0


# ==========================================
# Helper: رصيد المورد
# ==========================================
def get_supplier_balance(supplier_id):
    """جلب رصيد المورد الحالي"""
    row = db.query(
        """SELECT
             COALESCE((
                SELECT SUM(pi.total_amount)
                FROM purchase_invoices pi
                WHERE pi.supplier_id = ? AND pi.status = 'POSTED'
             ), 0) AS total_invoiced,
             COALESCE((
                SELECT SUM(sp.amount)
                FROM supplier_payments sp
                WHERE sp.supplier_id = ?
             ), 0) AS total_paid""",
        (supplier_id, supplier_id),
        one=True
    )
    invoiced = float(row['total_invoiced'] or 0) if row else 0
    paid = float(row['total_paid'] or 0) if row else 0
    return {
        'invoiced': invoiced,
        'paid': paid,
        'balance': invoiced - paid
    }


# ==========================================
# Helper: عدد أوامر الشراء المعلقة للمورد
# ==========================================
def get_supplier_pending_po_count(supplier_id):
    """عدد أوامر الشراء المعتمدة غير المستلمة"""
    row = db.query(
        """SELECT COUNT(*) AS cnt
           FROM purchase_orders
           WHERE supplier_id = ?
             AND status IN ('APPROVED', 'PARTIAL')""",
        (supplier_id,),
        one=True
    )
    return int(row['cnt'] or 0) if row else 0

# ==========================================
# Helper: التحقق من صحة التاريخ (الفترة المالية)
# ==========================================
def check_period(date_str):
    """
    التحقق من صحة تاريخ الحركة حسب سياسات الفترة المالية

    Args:
        date_str: التاريخ بصيغة YYYY-MM-DD

    Returns:
        dict: {'ok': True} أو {'ok': False, 'message': '...', 'code': 400}
    """
    if not date_str:
        return {'ok': True}

    settings = get_accounting()

    # 1. منع القيود بأثر رجعي
    if not settings.get('allow_backdated_entries', True):
        today = datetime.now().strftime('%Y-%m-%d')
        if date_str < today:
            return {
                'ok': False,
                'message': f'القيود بأثر رجعي غير مسموح بها. التاريخ المُدخل: {date_str} | التاريخ الحالي: {today}',
                'code': 400
            }

    # 2. إغلاق الفترة المالية تلقائيًا
    if settings.get('auto_close_period'):
        start = settings.get('fiscal_period_start', '') or ''
        end = settings.get('fiscal_period_end', '') or ''

        if start and date_str < start:
            return {
                'ok': False,
                'message': f'التاريخ {date_str} قبل بداية الفترة المالية ({start})',
                'code': 400
            }
        if end and date_str > end:
            return {
                'ok': False,
                'message': f'التاريخ {date_str} بعد نهاية الفترة المالية ({end})',
                'code': 400
            }

    return {'ok': True}

# ==========================================
# Helper: تحديد المستودع حسب multi_warehouse
# ==========================================
def resolve_warehouse(warehouse_id_from_request=None):
    """
    تحديد المستودع المناسب حسب سياسة multi_warehouse

    Args:
        warehouse_id_from_request: المستودع اللي جاي من الطلب (قد يكون None)

    Returns:
        dict: {'ok': True, 'warehouse_id': X} أو
              {'ok': False, 'message': '...', 'code': 400}
    """
    settings = get_inventory()

    # لو multi_warehouse مفعّل → استخدم المُدخل
    if settings.get('multi_warehouse', True):
        if not warehouse_id_from_request:
            return {
                'ok': False,
                'message': 'warehouse_id مطلوب',
                'code': 400
            }
        return {'ok': True, 'warehouse_id': int(warehouse_id_from_request)}

    # multi_warehouse معطّل → استخدم الافتراضي
    default_wh = settings.get('default_warehouse_id', '') or ''
    if not default_wh:
        return {
            'ok': False,
            'message': 'تعدد المستودعات معطّل، لكن مفيش مستودع افتراضي محدد. حدده من الإعدادات > سياسات المخازن.',
            'code': 400
        }

    try:
        return {'ok': True, 'warehouse_id': int(default_wh)}
    except (ValueError, TypeError):
        return {
            'ok': False,
            'message': f'default_warehouse_id غير صالح: {default_wh}',
            'code': 400
        }

# ==========================================
# Helpers: cost_method
# ==========================================
def get_cost_method(item_id=None):
    """
    تحديد طريقة التكلفة:
    - لو item_id محدد → استخدم items.cost_method
    - وإلا → استخدم accounting.cost_method
    """
    if item_id:
        row = db.query("SELECT cost_method FROM items WHERE id=?", (item_id,), one=True)
        if row and row['cost_method']:
            return row['cost_method']

    settings = get_accounting()
    return settings.get('cost_method', 'WEIGHTED_AVERAGE')


def get_default_cost_method():
    """طريقة التكلفة الافتراضية (من settings)"""
    settings = get_accounting()
    return settings.get('cost_method', 'WEIGHTED_AVERAGE')


# ==========================================
# Helper محدّث: طريقة التكلفة الافتراضية العامة
# ==========================================
def get_default_cost_method():
    """
    طريقة التكلفة الافتراضية العامة
    ✅ الأولوية: inventory ← الأول
                accounting ← الثاني
                WEIGHTED_AVERAGE ← الافتراضي
    """
    # 1. inventory
    inv = get_inventory()
    method = inv.get('default_cost_method') or inv.get('cost_method')
    if method:
        return method
    
    # 2. accounting (للتوافق)
    acc = get_accounting()
    method = acc.get('cost_method') or acc.get('default_cost_method')
    if method:
        return method
    
    # 3. افتراضي
    return 'WEIGHTED_AVERAGE'


# ==========================================
# Helper محدّث: طريقة التكلفة الافتراضية العامة
# ==========================================
def get_default_cost_method():
    """
    طريقة التكلفة الافتراضية العامة
    ✅ الأولوية: inventory ← الأول
                accounting ← الثاني
                WEIGHTED_AVERAGE ← الافتراضي
    """
    # 1. inventory
    inv = get_inventory()
    method = inv.get('default_cost_method') or inv.get('cost_method')
    if method:
        return method
    
    # 2. accounting (للتوافق)
    acc = get_accounting()
    method = acc.get('cost_method') or acc.get('default_cost_method')
    if method:
        return method
    
    # 3. افتراضي
    return 'WEIGHTED_AVERAGE'


# ==========================================
# Helper محدّث: طريقة التكلفة الافتراضية العامة
# ==========================================
def get_default_cost_method():
    """
    طريقة التكلفة الافتراضية العامة
    ✅ الأولوية: inventory ← الأول
                accounting ← الثاني
                WEIGHTED_AVERAGE ← الافتراضي
    """
    # 1. inventory
    inv = get_inventory()
    method = inv.get('default_cost_method') or inv.get('cost_method')
    if method:
        return method
    
    # 2. accounting (للتوافق)
    acc = get_accounting()
    method = acc.get('cost_method') or acc.get('default_cost_method')
    if method:
        return method
    
    # 3. افتراضي
    return 'WEIGHTED_AVERAGE'
