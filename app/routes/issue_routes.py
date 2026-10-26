from flask import Blueprint, request, jsonify
from app.database import db
from app.services.valuation_service import valuation_service
from app.services.settings_service import get_inventory, get_accounting, check_period, resolve_warehouse, get_cost_method
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service

issue_bp = Blueprint('issues', __name__)


def _next_txn_no(conn, prefix, txn_type):
    from datetime import datetime
    cur = conn.execute(
        """SELECT COUNT(*) as n FROM stock_transactions
           WHERE transaction_type=? AND strftime('%Y', created_at)=strftime('%Y','now')""",
        (txn_type,)
    )
    n = cur.fetchone()['n'] + 1
    return f"{prefix}-{datetime.now().year}-{n:06d}"


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


@issue_bp.route('/', methods=['GET'])
def list_issues():
    rows = db.query(
        """SELECT t.*, w.name_ar as warehouse_name
           FROM stock_transactions t
           LEFT JOIN warehouses w ON t.from_warehouse_id = w.id
           WHERE t.transaction_type='ISSUE'
           ORDER BY t.id DESC LIMIT 100"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@issue_bp.route('/<int:tid>', methods=['GET'])
def get_issue(tid):
    txn = db.query("SELECT * FROM stock_transactions WHERE id=?", (tid,), one=True)
    if not txn:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, i.name_ar as item_name FROM stock_transaction_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.transaction_id=? ORDER BY l.line_no""",
        (tid,)
    )
    txn['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(txn)})




# ==========================================
# دوال التحقق من سياسات المخازن
# ==========================================

def _validate_issue_policies(warehouse_id, lines):
    """
    التحقق من سياسات المخازن قبل إنشاء إذن صرف
    - allow_negative_stock: منع الصرف بأكثر من المخزون
    """
    inv_settings = get_inventory()

    # فحص المخزون السالب
    if not inv_settings.get('allow_negative_stock'):
        for line in lines:
            item_id = line.get('item_id')
            qty = float(line.get('quantity', 0))

            # جيب الوحدة الأساسية
            factor, base_qty = _get_base_quantity_ro(item_id, line.get('uom_id'), qty)
            if base_qty is None:
                continue

            # جيب الرصيد
            row = db.query(
                """SELECT COALESCE(SUM(quantity), 0) AS q
                   FROM stock_balances
                   WHERE warehouse_id=? AND item_id=?""",
                (warehouse_id, item_id), one=True
            )
            available = float(row['q'] or 0)

            if float(base_qty) > available:
                item = db.query(
                    "SELECT code, name_ar FROM items WHERE id=?",
                    (item_id,), one=True
                )
                item_label = f"{item['code']} - {item['name_ar']}" if item else f"#{item_id}"
                return {
                    'ok': False,
                    'message': f"المخزون غير كافي للصرف - الصنف: {item_label} | المطلوب: {base_qty} | المتاح: {available}",
                    'code': 400
                }

    return {'ok': True}


def _get_base_quantity_ro(item_id, uom_id, quantity):
    """نسخة read-only للحصول على الكمية الأساسية"""
    try:
        if not uom_id:
            return 1, float(quantity)

        row = db.query(
            "SELECT base_uom_id, medium_uom_id, medium_to_minor_factor, major_uom_id, major_to_medium_factor FROM items WHERE id=?",
            (item_id,), one=True
        )
        if not row:
            return 1, float(quantity)

        base_uom_id = row['base_uom_id']
        if int(uom_id) == int(base_uom_id):
            return 1, float(quantity)

        if row['medium_uom_id'] and int(uom_id) == int(row['medium_uom_id']):
            factor = float(row['medium_to_minor_factor'] or 1)
            return factor, float(quantity) * factor

        if row['major_uom_id'] and int(uom_id) == int(row['major_uom_id']):
            factor = float(row['major_to_medium_factor'] or 1) * float(row['medium_to_minor_factor'] or 1)
            return factor, float(quantity) * factor

        return 1, float(quantity)
    except Exception:
        return 1, float(quantity)



@issue_bp.route('/', methods=['POST'])
def create_issue():
    d = request.get_json() or {}
    if not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    # فحص سياسات المخازن
    v = _validate_issue_policies(d['warehouse_id'], d['lines'])
    if not v['ok']:
        return jsonify({'success': False, 'message': v['message']}), v.get('code', 400)

    # فحص الفترة المالية
    from datetime import datetime
    _date = d.get('transaction_date', '2026-01-01')
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
        txn_no = _next_txn_no(conn, 'ISS', 'ISSUE')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by)
               VALUES (?, 'ISSUE', ?, ?, ?, ?, 'DRAFT', ?, 1)""",
            (txn_no, d.get('transaction_date', '2026-01-01'),
             d['warehouse_id'], d.get('reference_type'),
             d.get('reference_no'), d.get('notes'))
        )
        txn_id = cur.lastrowid

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(
                conn, line['item_id'], line['uom_id'], line['quantity']
            )
            if base_qty is None:
                return jsonify({'success': False, 'message': f'الوحدة غير مرتبطة بالصنف'}), 400

            # Get avg cost from warehouse
            cur = conn.execute(
                """SELECT COALESCE(SUM(quantity),0) as q,
                          COALESCE(SUM(total_value),0) as v
                   FROM stock_balances
                   WHERE warehouse_id=? AND item_id=?""",
                (d['warehouse_id'], line['item_id'])
            )
            bal = cur.fetchone()
            avg_cost = (float(bal['v'])/float(bal['q'])) if bal and float(bal['q'])>0 else 0
            total_cost = round_decimal(to_decimal(base_qty) * to_decimal(avg_cost))

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity,
                    base_quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 float(line['quantity']), float(base_qty),
                 float(avg_cost), float(total_cost),
                 line.get('batch_no') or '')
            )

        cur = conn.execute(
            """SELECT COALESCE(SUM(base_quantity),0) as q,
                      COALESCE(SUM(total_cost),0) as v
               FROM stock_transaction_lines WHERE transaction_id=?""",
            (txn_id,)
        )
        tot = cur.fetchone()
        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (float(tot['q']), float(round_decimal(tot['v'])), txn_id)
        )

    return jsonify({'success': True, 'data': {'id': txn_id, 'transaction_no': txn_no}}), 201


@issue_bp.route('/<int:tid>/post', methods=['POST'])
def post_issue(tid):
    with db.transaction() as conn:
        cur = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND status='DRAFT'", (tid,)
        )
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الحركة غير موجودة أو مرحّلة'}), 404
        txn = dict(txn)

        cur = conn.execute(
            """SELECT l.*, i.name_ar, i.item_type FROM stock_transaction_lines l
               JOIN items i ON l.item_id = i.id
               WHERE l.transaction_id=?""",
            (tid,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        # Check total availability first (aggregate per item)
        needed = {}
        for line in lines:
            item_id = line['item_id']
            needed[item_id] = needed.get(item_id, 0) + float(line['base_quantity'] or line['quantity'])

        for item_id, need in needed.items():
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (txn['from_warehouse_id'], item_id)
            )
            avail = float(cur.fetchone()['q'])
            if avail < need:
                return jsonify({
                    'success': False,
                    'message': f'الكمية غير كافية للصنف. المتاح: {avail}، المطلوب: {need}'
                }), 400

        # Deduct from stock
        for line in lines:
            base_qty = float(line['base_quantity'] or line['quantity'])
            # batch_tracking: اختيار batch
            _batch_enabled = bool(get_inventory().get('batch_tracking', False))
            _expiry_enabled = bool(get_inventory().get('expiry_tracking', False))
            _wh_id = txn['from_warehouse_id']

            if _batch_enabled and not line.get('batch_no'):
                if _expiry_enabled:
                    _order = "CASE WHEN expiry_date IS NULL OR expiry_date = '' THEN 1 ELSE 0 END, expiry_date ASC, id ASC"
                else:
                    _order = "id ASC"
                _cur = conn.execute(f"""
                    SELECT id, batch_no, quantity FROM stock_balances
                    WHERE warehouse_id=? AND item_id=? AND quantity > 0
                    ORDER BY {_order}
                    LIMIT 1
                """, (_wh_id, line['item_id']))
                _b = _cur.fetchone()
                if _b:
                    line['batch_no'] = _b['batch_no']

            if _batch_enabled and line.get('batch_no'):
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity = quantity - ?,
                           total_value = total_value - ?
                       WHERE warehouse_id=? AND item_id=? AND batch_no=?""",
                    (base_qty, line['total_cost'], _wh_id, line['item_id'], line['batch_no'])
                )
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
                    (base_qty, line['total_cost'],
                     base_qty, line['total_cost'], base_qty,
                     _wh_id, line['item_id'])
                )
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
                        conn, txn['from_warehouse_id'], line['item_id'], base_qty, 'FIFO'
                    )
                    valuation_service.consume_layers(conn, result.get('consumed_layers', []))
            except Exception as e:
                print(f"WARN: consume_layers failed for item {line['item_id']}: {e}")

        # فحص القيد التلقائي
        acc_settings = get_accounting()
        if acc_settings.get('auto_journal_issues', True):
            je_id = accounting_service.create_journal_entry(conn, txn, lines)
        else:
            je_id = None

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, tid)
        )

    return jsonify({'success': True, 'message': 'تم الترحيل', 'data': {'journal_entry_id': je_id}})
