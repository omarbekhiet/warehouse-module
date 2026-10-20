from flask import Blueprint, request, jsonify
from app.database import db
from app.services.settings_service import (
    get_customers, get_accounting, get_inventory,
    get_customer_balance, get_overdue_invoices_count,
    get_cost_method
, check_period,
    resolve_warehouse
)
from app.services.valuation_service import valuation_service
from app.utils import json_safe, to_decimal, round_decimal, get_user_id, enrich_with_user
from datetime import datetime

sales_bp = Blueprint('sales_invoices', __name__)


def _next_invoice_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM sales_invoices")
    return f"SINV-{datetime.now().year}-{cur.fetchone()['n']:06d}"


def _next_txn_no(conn, prefix, txn_type):
    cur = conn.execute(
        "SELECT COUNT(*) as n FROM stock_transactions WHERE transaction_type=? AND strftime('%Y', created_at)=strftime('%Y','now')",
        (txn_type,)
    )
    return f"{prefix}-{datetime.now().year}-{cur.fetchone()['n']+1:06d}"


def _get_base_quantity(conn, item_id, uom_id, quantity):
    item = conn.execute(
        "SELECT base_uom_id, medium_uom_id, medium_to_minor_factor, major_uom_id, major_to_medium_factor FROM items WHERE id=?",
        (item_id,)
    ).fetchone()
    if not item:
        return None, None
    if int(uom_id) == int(item['base_uom_id']):
        factor = 1.0
    elif item['medium_uom_id'] and int(uom_id) == int(item['medium_uom_id']):
        factor = float(item['medium_to_minor_factor'] or 1)
    elif item['major_uom_id'] and int(uom_id) == int(item['major_uom_id']):
        factor = float(item['major_to_medium_factor'] or 1) * float(item['medium_to_minor_factor'] or 1)
    else:
        return None, None
    return factor, float(quantity) * factor


@sales_bp.route('/', methods=['GET'])
def list_sales():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('si.status = ?')
        vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT si.*, c.name_ar as customer_name, w.name_ar as warehouse_name
            FROM sales_invoices si
            LEFT JOIN customers c ON si.customer_id = c.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE {where}
            ORDER BY si.id DESC LIMIT 200""",
        vals
    )
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})
    

@sales_bp.route('/<int:inv_id>', methods=['GET'])
def get_sale(inv_id):
    inv = db.query(
        """SELECT si.*, c.name_ar as customer_name, c.code as customer_code,
                  w.name_ar as warehouse_name
           FROM sales_invoices si
           LEFT JOIN customers c ON si.customer_id = c.id
           LEFT JOIN warehouses w ON si.warehouse_id = w.id
           WHERE si.id=?""",
        (inv_id,), one=True
    )
    if not inv:
        return jsonify({'success': False, 'message': 'غير موجودة'}), 404
    lines = db.query(
        """SELECT sil.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name, u.code as uom_code
           FROM sales_invoice_lines sil
           JOIN items i ON sil.item_id = i.id
           LEFT JOIN units_of_measure u ON sil.uom_id = u.id
           WHERE sil.invoice_id=? ORDER BY sil.line_no""",
        (inv_id,)
    )
    inv['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(inv)})




# ==========================================
# دوال التحقق من السياسات
# ==========================================

def _validate_sale_policies(customer_id, warehouse_id, lines, current_invoice_id=None):
    """
    التحقق من سياسات العملاء والمخازن قبل إنشاء/تعديل فاتورة

    Returns:
        dict: {'ok': True} لو تمام، أو {'ok': False, 'message': '...', 'code': 400}
    """
    cust_settings = get_customers()
    acc_settings = get_accounting()
    inv_settings = get_inventory()

    # 1. التحقق من العميل
    customer = db.query(
        "SELECT id, name_ar, payment_terms FROM customers WHERE id=?",
        (customer_id,), one=True
    )
    if not customer:
        return {'ok': False, 'message': 'العميل غير موجود', 'code': 404}

    # 1.1 منع البيع للعملاء المتأخرين
    if cust_settings.get('block_overdue_customers'):
        overdue_count = get_overdue_invoices_count(
            customer_id,
            payment_terms=customer['payment_terms']
        )
        if overdue_count > 0:
            terms = customer['payment_terms'] or cust_settings.get('default_payment_terms', 30)
            return {
                'ok': False,
                'message': "لا يمكن البيع - العميل '" + customer['name_ar'] + "' لديه " + str(overdue_count) + " فاتورة متأخرة (مدة السماح: " + str(terms) + " يوم)",
                'code': 400
            }

    # 1.2 حد الائتمان
    credit_limit = cust_settings.get('default_credit_limit', 0)
    if credit_limit and float(credit_limit) > 0:
        cust_limit_row = db.query(
            "SELECT credit_limit FROM customers WHERE id=?",
            (customer_id,), one=True
        )
        if cust_limit_row and cust_limit_row['credit_limit'] and float(cust_limit_row['credit_limit']) > 0:
            credit_limit = float(cust_limit_row['credit_limit'])

        new_invoice_total = 0
        for ln in lines:
            qty = float(ln.get('quantity', 0))
            price = float(ln.get('unit_price', 0))
            disc = float(ln.get('discount_pct', 0))
            line_sub = qty * price * (1 - disc / 100)
            new_invoice_total += line_sub

        if current_invoice_id:
            old_inv = db.query(
                "SELECT total_amount FROM sales_invoices WHERE id=?",
                (current_invoice_id,), one=True
            )
            if old_inv:
                bal = get_customer_balance(customer_id)
                current_balance = bal['balance'] - float(old_inv['total_amount'] or 0)
            else:
                current_balance = get_customer_balance(customer_id)['balance']
        else:
            current_balance = get_customer_balance(customer_id)['balance']

        new_balance = current_balance + new_invoice_total
        if new_balance > float(credit_limit):
            remaining = float(credit_limit) - current_balance
            msg = "تجاوز حد الائتمان - الحد: " + str(round(credit_limit, 2)) + " ج.م | الرصيد: " + str(round(current_balance, 2)) + " | المتاح: " + str(round(remaining, 2)) + " | الفاتورة: " + str(round(new_invoice_total, 2))
            return {'ok': False, 'message': msg, 'code': 400}

    # 2. التحقق من المخزون
    if not inv_settings.get('allow_negative_stock'):
        for line in lines:
            item_id = line.get('item_id')
            qty = float(line.get('quantity', 0))

            factor, base_qty = _get_base_quantity_ro(item_id, line.get('uom_id'), qty)
            if base_qty is None:
                continue

            row = db.query(
                """SELECT COALESCE(SUM(quantity), 0) AS q
                   FROM stock_balances
                   WHERE warehouse_id=? AND item_id=?""",
                (warehouse_id, item_id), one=True
            )
            available = float(row['q'] or 0)

            if current_invoice_id:
                old_line = db.query(
                    """SELECT base_quantity FROM sales_invoice_lines
                       WHERE invoice_id=? AND item_id=?""",
                    (current_invoice_id, item_id), one=True
                )
                if old_line:
                    available += float(old_line['base_quantity'] or 0)

            if float(base_qty) > available:
                item = db.query(
                    "SELECT code, name_ar FROM items WHERE id=?",
                    (item_id,), one=True
                )
                item_label = (item['code'] + " - " + item['name_ar']) if item else ("#" + str(item_id))
                msg = "المخزون غير كافي - الصنف: " + item_label + " | المطلوب: " + str(base_qty) + " | المتاح: " + str(available)
                return {'ok': False, 'message': msg, 'code': 400}

    return {'ok': True}


def _get_base_quantity_ro(item_id, uom_id, quantity):
    """نسخة read-only من _get_base_quantity (بدون conn)"""
    try:
        if not uom_id:
            return 1, float(quantity)

        row = db.query(
            "SELECT base_uom_id FROM items WHERE id=?",
            (item_id,), one=True
        )
        if not row:
            return 1, float(quantity)

        base_uom_id = row['base_uom_id']

        if base_uom_id == uom_id:
            return 1, float(quantity)

        conv = db.query(
            """SELECT factor FROM uom_conversions
               WHERE item_id=? AND from_uom_id=? AND to_uom_id=?""",
            (item_id, uom_id, base_uom_id), one=True
        )
        if conv:
            factor = float(conv['factor'])
            return factor, float(quantity) * factor

        return 1, float(quantity)
    except Exception:
        return 1, float(quantity)



@sales_bp.route('/', methods=['POST'])

def create_sale():
    default_discount = float(get_customers().get('default_discount', 0))
    d = request.get_json() or {}
    if not d.get('customer_id') or not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    # فحص السياسات
    v = _validate_sale_policies(d['customer_id'], d['warehouse_id'], d['lines'])
    if not v['ok']:
        return jsonify({'success': False, 'message': v['message']}), v.get('code', 400)

    # فحص الفترة المالية
    from datetime import datetime
    _date = d.get('invoice_date', datetime.now().strftime('%Y-%m-%d'))
    _period_check = check_period(_date)
    if not _period_check['ok']:
        return jsonify({'success': False, 'message': _period_check['message']}), _period_check.get('code', 400)

    # فحص multi_warehouse
    _wh_input = d.get('warehouse_id') if 'd' in dir() else None
    wh_result = resolve_warehouse(_wh_input)
    if not wh_result['ok']:
        return jsonify({'success': False, 'message': wh_result['message']}), wh_result.get('code', 400)
    d['warehouse_id'] = wh_result['warehouse_id']


    with db.transaction() as conn:
        inv_no = _next_invoice_no(conn)
        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO sales_invoices
               (invoice_no, invoice_date, customer_id, warehouse_id,
                tax_rate, status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, ?)""",
            (inv_no, d.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
             d['customer_id'], d['warehouse_id'],
             d.get('tax_rate', get_accounting().get('default_vat_rate', 14)), d.get('notes'), user_id)
        )
        inv_id = cur.lastrowid

        subtotal = 0
        tax_total = 0
        cogs_total = 0

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            # Get avg cost
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q, COALESCE(SUM(total_value),0) as v FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (d['warehouse_id'], line['item_id'])
            )
            bal = cur.fetchone()
            available = float(bal['q']) if bal else 0
            total_val = float(bal['v']) if bal else 0
            avg_cost = (total_val / available) if available > 0 else 0
            line_cost = float(base_qty) * avg_cost
            cogs_total += line_cost

            qty = float(line['quantity'])
            price = float(line['unit_price'])
            disc_pct = float(line.get('discount_pct', default_discount))
            tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
            line_sub = qty * price * (1 - disc_pct/100)
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax

            conn.execute(
                """INSERT INTO sales_invoice_lines
                   (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, unit_cost, discount_pct, tax_rate,
                    line_subtotal, line_tax, line_total, line_cost)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (inv_id, i, line['item_id'], line['uom_id'],
                 qty, base_qty, price, avg_cost, disc_pct, tax_rate,
                 line_sub, line_tax, line_total, line_cost)
            )
            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE sales_invoices SET subtotal=?, tax_amount=?, total_amount=?, cogs_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), round(cogs_total, 2), inv_id)
        )

    return jsonify({'success': True, 'data': {'id': inv_id, 'invoice_no': inv_no}}), 201


@sales_bp.route('/<int:inv_id>', methods=['PUT'])
def update_sale(inv_id):
    default_discount = float(get_customers().get('default_discount', 0))
    d = request.get_json() or {}
    # فحص السياسات
    if d.get('customer_id') and d.get('warehouse_id') and d.get('lines'):
        v = _validate_sale_policies(
            d['customer_id'], d['warehouse_id'], d['lines'],
            current_invoice_id=inv_id
        )
        if not v['ok']:
            return jsonify({'success': False, 'message': v['message']}), v.get('code', 400)

    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل فاتورة مرحّلة'}), 400

        conn.execute(
            """UPDATE sales_invoices
               SET invoice_date=?, customer_id=?, warehouse_id=?, tax_rate=?, notes=?
               WHERE id=?""",
            (d.get('invoice_date'), d['customer_id'], d['warehouse_id'],
             d.get('tax_rate', 14), d.get('notes'), inv_id)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM sales_invoice_lines WHERE invoice_id=?", (inv_id,))
            subtotal = 0
            tax_total = 0
            cogs_total = 0
            for i, line in enumerate(d['lines'], start=1):
                factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
                if base_qty is None:
                    return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400
                cur = conn.execute(
                    "SELECT COALESCE(SUM(quantity),0) as q, COALESCE(SUM(total_value),0) as v FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                    (d['warehouse_id'], line['item_id'])
                )
                bal = cur.fetchone()
                available = float(bal['q']) if bal else 0
                total_val = float(bal['v']) if bal else 0
                avg_cost = (total_val / available) if available > 0 else 0
                line_cost = float(base_qty) * avg_cost
                cogs_total += line_cost

                qty = float(line['quantity'])
                price = float(line['unit_price'])
                disc_pct = float(line.get('discount_pct', default_discount))
                tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
                line_sub = qty * price * (1 - disc_pct/100)
                line_tax = line_sub * tax_rate / 100
                line_total = line_sub + line_tax

                conn.execute(
                    """INSERT INTO sales_invoice_lines
                       (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                        unit_price, unit_cost, discount_pct, tax_rate,
                        line_subtotal, line_tax, line_total, line_cost)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (inv_id, i, line['item_id'], line['uom_id'],
                     qty, base_qty, price, avg_cost, disc_pct, tax_rate,
                     line_sub, line_tax, line_total, line_cost)
                )
                subtotal += line_sub
                tax_total += line_tax

            conn.execute(
                "UPDATE sales_invoices SET subtotal=?, tax_amount=?, total_amount=?, cogs_amount=? WHERE id=?",
                (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), round(cogs_total, 2), inv_id)
            )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@sales_bp.route('/<int:inv_id>/reject', methods=['POST'])
def reject_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row or row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن رفض المسودة فقط'}), 400
        conn.execute("UPDATE sales_invoices SET status='REJECTED' WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@sales_bp.route('/<int:inv_id>/restore', methods=['POST'])
def restore_sale(inv_id):
    with db.transaction() as conn:
        conn.execute("UPDATE sales_invoices SET status='DRAFT' WHERE id=? AND status='REJECTED'", (inv_id,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@sales_bp.route('/<int:inv_id>', methods=['DELETE'])
def delete_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row or row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف فاتورة مرحّلة'}), 400
        conn.execute("DELETE FROM sales_invoice_lines WHERE invoice_id=?", (inv_id,))
        conn.execute("DELETE FROM sales_invoices WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@sales_bp.route('/<int:inv_id>/post', methods=['POST'])
def post_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM sales_invoices WHERE id=? AND status IN ('DRAFT','REJECTED')", (inv_id,))
        inv = cur.fetchone()
        if not inv:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        inv = dict(inv)

        cur = conn.execute(
            """SELECT sil.*, i.item_type FROM sales_invoice_lines sil
               JOIN items i ON sil.item_id = i.id
               WHERE sil.invoice_id=?""",
            (inv_id,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        # Stock check
                # Stock check
        for line in lines:
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (inv['warehouse_id'], line['item_id'])
            )
            available = float(cur.fetchone()['q'])
            if available < float(line['base_quantity']):
                return jsonify({'success': False, 'message': f'الكمية غير كافية للصنف. المتاح: {available}'}), 400

        txn_no = _next_txn_no(conn, 'DEL', 'ISSUE')
        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by, invoice_id, invoice_type)
               VALUES (?, 'ISSUE', ?, ?, 'SALES_INVOICE', ?, 'DRAFT', ?, ?, ?, 'SALES')""",
            (txn_no, inv['invoice_date'], inv['warehouse_id'],
             inv['invoice_no'], f"صرف من فاتورة {inv['invoice_no']}", user_id, inv_id)
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_cost = 0
        for i, line in enumerate(lines, start=1):
            base_qty = float(line['base_quantity'])
            unit_cost_base = float(line['unit_cost'])
            line_cost = float(line['line_cost'])
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 line['quantity'], base_qty, unit_cost_base, line_cost)
            )
            # batch_tracking: اختيار batch
            _batch_enabled = bool(get_inventory().get('batch_tracking', False))
            _expiry_enabled = bool(get_inventory().get('expiry_tracking', False))
            _wh_id = inv['warehouse_id']

            if _batch_enabled and not line.get('batch_no'):
                # اختيار batch تلقائي
                if _expiry_enabled:
                    _order = "CASE WHEN expiry_date IS NULL OR expiry_date = '' THEN 1 ELSE 0 END, expiry_date ASC, id ASC"
                else:
                    _order = "id ASC"

                _cur = conn.execute(f"""
                    SELECT id, batch_no, quantity, average_cost
                    FROM stock_balances
                    WHERE warehouse_id=? AND item_id=? AND quantity > 0
                    ORDER BY {_order}
                    LIMIT 1
                """, (_wh_id, line['item_id']))
                _b = _cur.fetchone()
                if _b:
                    line['batch_no'] = _b['batch_no']

            # خصم من batch محدد أو الكل
            if _batch_enabled and line.get('batch_no'):
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity = quantity - ?,
                           total_value = total_value - ?
                       WHERE warehouse_id=? AND item_id=? AND batch_no=?""",
                    (base_qty, line_cost, _wh_id, line['item_id'], line['batch_no'])
                )
                # تحديث cost_layers للـ batch
                try:
                    cost_method = get_cost_method(line['item_id'])
                    if cost_method == 'FIFO':
                        result = valuation_service.calculate(
                            conn, _wh_id, line['item_id'], base_qty, 'FIFO'
                        )
                        valuation_service.consume_layers(conn, result.get('consumed_layers', []))
                except Exception as e:
                    print(f"WARN: consume_layers failed: {e}")
            else:
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity = quantity - ?,
                           total_value = total_value - ?,
                           average_cost = CASE WHEN quantity - ? > 0
                             THEN (total_value - ?) / (quantity - ?) ELSE 0 END
                       WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                    (base_qty, line_cost, base_qty, line_cost, base_qty,
                     _wh_id, line['item_id'])
                )
                # cost_layers
                try:
                    cost_method = get_cost_method(line['item_id'])
                    if cost_method == 'FIFO':
                        result = valuation_service.calculate(
                            conn, _wh_id, line['item_id'], base_qty, 'FIFO'
                        )
                        valuation_service.consume_layers(conn, result.get('consumed_layers', []))
                except Exception as e:
                    print(f"WARN: consume_layers failed: {e}")

            # خصم من cost_layers للـ FIFO
            try:
                cost_method = get_cost_method(line['item_id'])
                if cost_method == 'FIFO':
                    result = valuation_service.calculate(
                        conn, inv['warehouse_id'], line['item_id'], base_qty, 'FIFO'
                    )
                    valuation_service.consume_layers(conn, result.get('consumed_layers', []))
            except Exception as e:
                # لو الكمية غير كافية أو خطأ → نتجاهل
                print(f"WARN: consume_layers failed for item {line['item_id']}: {e}")

            total_qty += base_qty
            total_cost += line_cost

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_cost, 4), txn_id)
        )

        # فحص القيد التلقائي — لو معطّل، نرحّل بدون قيد
        acc_settings = get_accounting()
        if not acc_settings.get('auto_journal_invoices', True):
            conn.execute(
                "UPDATE sales_invoices SET status='POSTED', stock_txn_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
                (txn_id, inv_id)
            )
            conn.execute(
                "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP WHERE id=?",
                (txn_id,)
            )
            return jsonify({
                'success': True,
                'message': 'تم الترحيل (بدون قيد محاسبي)',
                'data': {'invoice_id': inv_id, 'stock_txn_id': txn_id, 'journal_entry_id': None}
            })

        # القيد التلقائي (كما هو)
                # القيد التلقائي (كما هو)
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status, created_by)
               VALUES (?, ?, 'SALES_INVOICE', ?, ?, ?, 'POSTED', ?)""",
            (je_no, inv['invoice_date'], inv_id, inv['invoice_no'], f"قيد فاتورة بيع {inv['invoice_no']}", user_id)
        )
        je_id = cur.lastrowid

        line_no = 1
        td = 0
        tc = 0

        # Debit: AR (آجل) أو Cash (نقدي)
        payment_type = inv.get('payment_type', 'CREDIT')
        payment_method_code = inv.get('payment_method_code')
        
        if payment_type == 'CASH':
            method_accounts = {
                'CASH':           '1211',
                'BANK_TRANSFER':  '1212',
                'CHEQUE':         '1225',
                'CARD':           '1213',
                'WALLET':         '1214',
            }
            debit_account = method_accounts.get(payment_method_code, '1211')
            debit_desc = f'نقدية - {payment_method_code or "CASH"}'
        else:
            debit_account = '1221'
            debit_desc = 'ذمم العملاء'
        
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (je_id, line_no, debit_account, debit_desc, round(float(inv['total_amount']), 2))
        )
        td += float(inv['total_amount']); line_no += 1

        # Credit Revenue
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '4111', 'إيرادات المبيعات', 0, ?)""",
            (je_id, line_no, round(float(inv['subtotal']), 2))
        )
        tc += float(inv['subtotal']); line_no += 1

        # Credit VAT Output
        if float(inv['tax_amount']) > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, '2231', 'ضريبة مخرجات', 0, ?)""",
                (je_id, line_no, round(float(inv['tax_amount']), 2))
            )
            tc += float(inv['tax_amount']); line_no += 1

        # COGS
        inv_by_account = {}
        for line in lines:
            item_info = conn.execute("SELECT inventory_account FROM items WHERE id=?", (line['item_id'],)).fetchone()
            acc = item_info['inventory_account'] if item_info else '1234'
            inv_by_account[acc] = inv_by_account.get(acc, 0) + float(line['line_cost'])

        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '3000', 'تكلفة المبيعات', ?, 0)""",
            (je_id, line_no, round(float(inv['cogs_amount']), 2))
        )
        td += float(inv['cogs_amount']); line_no += 1

        for acc, amount in inv_by_account.items():
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, ?, 'مخزون مصروف', 0, ?)""",
                (je_id, line_no, acc, round(amount, 2))
            )
            tc += amount; line_no += 1

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (round(td, 2), round(tc, 2), je_id))

        conn.execute(
            "UPDATE sales_invoices SET status='POSTED', stock_txn_id=?, journal_entry_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
            (txn_id, je_id, inv_id)
        )
        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, txn_id)
        )

    return jsonify({
        'success': True,
        'message': 'تم ترحيل الفاتورة',
        'data': {'invoice_id': inv_id, 'stock_txn_id': txn_id, 'journal_entry_id': je_id}
    })
