from app.utils import json_safe, to_decimal, round_decimal, get_user_id, enrich_with_user
from flask import Blueprint, request, jsonify
from app.database import db
from app.services.settings_service import get_inventory, check_period, resolve_warehouse, get_cost_method
from app.services.valuation_service import valuation_service
from datetime import datetime

count_bp = Blueprint('counts', __name__)


def _next_count_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM inventory_counts")
    n = cur.fetchone()['n']
    return f"CNT-{datetime.now().year}-{n:06d}"


@count_bp.route('/', methods=['GET'])
def list_counts():
    rows = db.query(
        """SELECT ic.*, w.name_ar as warehouse_name
           FROM inventory_counts ic
           LEFT JOIN warehouses w ON ic.warehouse_id = w.id
           ORDER BY ic.id DESC LIMIT 100"""
    )
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})



@count_bp.route('/<int:cid>', methods=['GET'])
def get_count(cid):
    row = db.query("SELECT * FROM inventory_counts WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, i.name_ar as item_name, i.code as item_code,
                  (l.counted_qty - l.system_qty) as variance_qty
           FROM inventory_count_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.count_id=?""",
        (cid,)
    )
    row['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(row)})


@count_bp.route('/', methods=['POST'])
def create_count():
    d = request.get_json() or {}
    if not d.get('warehouse_id'):
        return jsonify({'success': False, 'message': 'warehouse_id مطلوب'}), 400
    with db.transaction() as conn:
        count_no = _next_count_no(conn)
        cur = conn.execute(
            """INSERT INTO inventory_counts
               (count_no, warehouse_id, count_date, count_type, status)
               VALUES (?, ?, ?, ?, 'DRAFT')""",
            (count_no, d['warehouse_id'],
             d.get('count_date', datetime.now().strftime('%Y-%m-%d')),
             d.get('count_type', 'FULL'))
        )
        cid = cur.lastrowid
        cur = conn.execute(
            "SELECT item_id, batch_no, quantity, average_cost FROM stock_balances WHERE warehouse_id=? AND quantity > 0",
            (d['warehouse_id'],)
        )
        for bal in cur.fetchall():
            conn.execute(
                """INSERT INTO inventory_count_lines
                   (count_id, item_id, system_qty, counted_qty, unit_cost)
                   VALUES (?, ?, ?, ?, ?)""",
                (cid, bal['item_id'], bal['quantity'], bal['quantity'], bal['average_cost'] or 0)
            )
    return jsonify({'success': True, 'data': {'id': cid, 'count_no': count_no}}), 201


@count_bp.route('/<int:cid>/count', methods=['PUT'])
def update_counted(cid):
    d = request.get_json() or {}
    lines = d.get('lines', [])
    if not lines:
        return jsonify({'success': False, 'message': 'لا توجد بنود'}), 400
    with db.transaction() as conn:
        for l in lines:
            conn.execute(
                """UPDATE inventory_count_lines 
                   SET counted_qty=?, variance_value=(? - system_qty) * unit_cost
                   WHERE id=? AND count_id=?""",
                (l['counted_qty'], l['counted_qty'], l['id'], cid)
            )
        conn.execute("UPDATE inventory_counts SET status='IN_PROGRESS' WHERE id=?", (cid,))
    return jsonify({'success': True, 'message': 'تم التحديث'})


@count_bp.route('/<int:cid>/post', methods=['POST'])
def post_count(cid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM inventory_counts WHERE id=? AND status IN ('DRAFT','IN_PROGRESS')", (cid,))
        count = cur.fetchone()
        if not count:
            return jsonify({'success': False, 'message': 'الجرد غير موجود أو مرحّل'}), 404
        count = dict(count)

        cur = conn.execute(
            """SELECT l.*, i.name_ar, i.item_type
               FROM inventory_count_lines l
               JOIN items i ON l.item_id = i.id
               WHERE l.count_id=? AND (l.counted_qty - l.system_qty) != 0""",
            (cid,)
        )
        lines = [dict(r) for r in cur.fetchall()]
        if not lines:
            return jsonify({'success': False, 'message': 'لا توجد فروق للتسوية'}), 400

        cur = conn.execute("SELECT COUNT(*)+1 as n FROM stock_transactions WHERE transaction_type='COUNT_ADJUST'")
        n = cur.fetchone()['n']
        txn_no = f"ADJ-{datetime.now().year}-{n:06d}"

        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, from_warehouse_id, reference_type,
                reference_id, reference_no, status, notes, created_by)
               VALUES (?, 'COUNT_ADJUST', ?, ?, ?, 'INVENTORY_COUNT', ?, ?, 'DRAFT', ?, ?)""",
            (txn_no, count['count_date'], count['warehouse_id'], count['warehouse_id'],
             count['id'], count['count_no'], f"تسوية جرد {count['count_no']}", user_id)
        )

        txn_id = cur.lastrowid

        adj_lines = []
        for i, line in enumerate(lines, start=1):
            variance = float(line['counted_qty']) - float(line['system_qty'])
            unit_cost = float(line['unit_cost']) or 0
            variance_value = variance * unit_cost
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, 1, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], variance, unit_cost, variance_value)
            )
            conn.execute(
                """UPDATE stock_balances
                   SET quantity = quantity + ?, total_value = total_value + ?
                   WHERE warehouse_id=? AND item_id=?""",
                (variance, variance_value, count['warehouse_id'], line['item_id'])
            )
            adj_lines.append({'item_id': line['item_id'], 'item_type': line['item_type'], 'total_cost': variance_value})

        conn.execute(
            """UPDATE stock_transactions SET
                 total_qty = (SELECT COALESCE(SUM(quantity),0) FROM stock_transaction_lines WHERE transaction_id=?),
                 total_value = (SELECT COALESCE(SUM(total_cost),0) FROM stock_transaction_lines WHERE transaction_id=?)
               WHERE id=?""",
            (txn_id, txn_id, txn_id)
        )

        entry_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"

        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status, created_by)
               VALUES (?, ?, 'INVENTORY_COUNT', ?, ?, ?, 'POSTED', ?)""",
            (entry_no, count['count_date'], cid, count['count_no'], f"قيد تسوية جرد {count['count_no']}", user_id)
        )

        je_id = cur.lastrowid

        line_no = 1
        td = 0
        tc = 0
        for line in adj_lines:
            v = line['total_cost']
            if v == 0:
                continue
            inv_acc = '1231'
            if line['item_type'] == 'MERCHANDISE':
                inv_acc = '1234'
            elif line['item_type'] == 'FINISHED_GOODS':
                inv_acc = '1233'
            elif line['item_type'] == 'SUPPLIES':
                inv_acc = '1235'

            if v > 0:
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, ?, 'زيادة جرد', ?, 0)""", (je_id, line_no, inv_acc, v))
                td += v
                line_no += 1
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, '4231', 'إيرادات - زيادة جرد', 0, ?)""", (je_id, line_no, v))
                tc += v
                line_no += 1
            else:
                av = abs(v)
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, '5563', 'عجز جرد', ?, 0)""", (je_id, line_no, av))
                td += av
                line_no += 1
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, ?, 'نقص مخزون', 0, ?)""", (je_id, line_no, inv_acc, av))
                tc += av
                line_no += 1

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?", (td, tc, je_id))
        conn.execute("""UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?""", (je_id, txn_id))
        conn.execute("""UPDATE inventory_counts SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?""", (je_id, cid))

    return jsonify({'success': True, 'message': 'تم ترحيل الجرد',
                    'data': {'count_id': cid, 'transaction_id': txn_id, 'transaction_no': txn_no, 'journal_entry_id': je_id}})


@count_bp.route('/<int:cid>', methods=['DELETE'])
def delete_count(cid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM inventory_counts WHERE id=?", (cid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف جرد مرحّل'}), 400
        conn.execute("DELETE FROM inventory_count_lines WHERE count_id=?", (cid,))
        conn.execute("DELETE FROM inventory_counts WHERE id=?", (cid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============================================================
# Quick Adjustment - تسوية مخزنية سريعة (عجز / زيادة)
# ============================================================

QUICK_REASONS = {
    'DAMAGE': 'تلف',
    'BREAKAGE': 'كسر',
    'LOSS': 'فقد',
    'THEFT': 'سرقة',
    'EXPIRY': 'انتهاء صلاحية',
    'SURPLUS': 'فائض جرد',
    'GIFT': 'هدية',
    'SAMPLE': 'عينة',
    'OPENING': 'رصيد افتتاحي',
    'OTHER': 'أخرى'
}


def _next_quick_no(conn):
    """رقم تسوية سريعة جديد"""
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM inventory_counts WHERE count_type='QUICK'")
    n = cur.fetchone()['n']
    return f"ADJ-{datetime.now().year}-{n:06d}"


def _get_inventory_account(item_type):
    """حساب المخزون حسب نوع الصنف"""
    if item_type == 'MERCHANDISE':
        return '1234'
    elif item_type == 'FINISHED_GOODS':
        return '1233'
    elif item_type == 'SUPPLIES':
        return '1235'
    return '1231'


@count_bp.route('/quick-adjustment', methods=['POST'])
def quick_adjustment():
    """تسوية مخزنية سريعة (عجز / زيادة)"""
    d = request.get_json() or {}

    inv_settings = get_inventory()

    if not inv_settings.get('allow_direct_adjustments'):
        return jsonify({
            'success': False,
            'message': 'التسويات المباشرة غير مفعّلة في إعدادات المخازن. الرجاء تفعيلها أو استخدام الجرد.'
        }), 400

    if inv_settings.get('require_adjustment_reason'):
        reason_check = d.get('reason', '').strip()
        if not reason_check or reason_check == 'OTHER':
            if not d.get('notes', '').strip():
                return jsonify({
                    'success': False,
                    'message': 'سبب التسوية مطلوب — يجب تحديد السبب أو إضافة ملاحظات'
                }), 400

    if not d.get('warehouse_id'):
        return jsonify({'success': False, 'message': 'warehouse_id مطلوب'}), 400

    adj_type = d.get('adjustment_type', '').upper()
    if adj_type not in ('SHORTAGE', 'SURPLUS'):
        return jsonify({'success': False, 'message': 'adjustment_type لازم يكون SHORTAGE أو SURPLUS'}), 400

    reason = d.get('reason', 'OTHER').upper()
    if reason not in QUICK_REASONS:
        return jsonify({'success': False, 'message': f'reason غير صالح. القيم المسموحة: {list(QUICK_REASONS.keys())}'}), 400

    lines = d.get('lines', [])
    if not lines:
        return jsonify({'success': False, 'message': 'لازم بند واحد على الأقل'}), 400

    warehouse_id = int(d['warehouse_id'])
    adj_date = d.get('adjustment_date') or datetime.now().strftime('%Y-%m-%d')
    notes = d.get('notes', '') or ''

    _date = d.get('adjustment_date') or datetime.now().strftime('%Y-%m-%d')
    _period_check = check_period(_date)
    if not _period_check['ok']:
        return jsonify({'success': False, 'message': _period_check['message']}), _period_check.get('code', 400)

    _wh_input = warehouse_id if 'warehouse_id' in dir() else None
    wh_result = resolve_warehouse(_wh_input)
    if not wh_result['ok']:
        return jsonify({'success': False, 'message': wh_result['message']}), wh_result.get('code', 400)
    warehouse_id = wh_result['warehouse_id']

    with db.transaction() as conn:
        cur = conn.execute("SELECT id, name_ar FROM warehouses WHERE id=?", (warehouse_id,))
        wh = cur.fetchone()
        if not wh:
            return jsonify({'success': False, 'message': 'المستودع غير موجود'}), 404
        wh = dict(wh)

        processed_lines = []
        total_value = 0

        for ln in lines:
            item_id = int(ln.get('item_id', 0))
            qty = float(ln.get('quantity', 0))

            if item_id <= 0 or qty <= 0:
                return jsonify({'success': False, 'message': 'كل بند لازم فيه item_id و quantity > 0'}), 400

            cur = conn.execute(
                "SELECT id, code, name_ar, item_type FROM items WHERE id=?",
                (item_id,)
            )
            item = cur.fetchone()
            if not item:
                return jsonify({'success': False, 'message': f'الصنف {item_id} غير موجود'}), 404
            item = dict(item)

            cur = conn.execute(
                """SELECT quantity, average_cost, total_value
                   FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (warehouse_id, item_id)
            )
            bal = cur.fetchone()
            system_qty = float(bal['quantity']) if bal else 0
            avg_cost = float(bal['average_cost']) if bal else 0

            if adj_type == 'SHORTAGE' and system_qty < qty:
                return jsonify({
                    'success': False,
                    'message': f'الكمية المطلوب خصمها ({qty}) أكبر من الرصيد المتاح ({system_qty}) للصنف {item["code"]}'
                }), 400

            unit_cost = float(ln.get('unit_cost', 0)) or avg_cost
            if unit_cost <= 0 and adj_type == 'SHORTAGE':
                return jsonify({
                    'success': False,
                    'message': f'الصنف {item["code"]} مالوش تكلفة. حدد unit_cost يدويًا.'
                }), 400
            if unit_cost <= 0:
                unit_cost = avg_cost or 1.0

            if adj_type == 'SHORTAGE':
                counted_qty = system_qty - qty
                variance_qty = -qty
            else:
                counted_qty = system_qty + qty
                variance_qty = qty

            variance_value = variance_qty * unit_cost
            total_value += variance_value

            processed_lines.append({
                'item_id': item_id,
                'item_code': item['code'],
                'item_name': item['name_ar'],
                'item_type': item['item_type'],
                'system_qty': system_qty,
                'counted_qty': counted_qty,
                'variance_qty': variance_qty,
                'unit_cost': unit_cost,
                'variance_value': variance_value
            })

        quick_no = _next_quick_no(conn)
        reason_ar = QUICK_REASONS[reason]
        type_ar = 'عجز' if adj_type == 'SHORTAGE' else 'زيادة'
        full_notes = f"[{type_ar}] السبب: {reason_ar}"
        if notes:
            full_notes += f" | {notes}"

        cur = conn.execute(
            """INSERT INTO inventory_counts
               (count_no, warehouse_id, count_date, count_type, status, notes)
               VALUES (?, ?, ?, 'QUICK', 'DRAFT', ?)""",
            (quick_no, warehouse_id, adj_date, full_notes)
        )
        count_id = cur.lastrowid

        for p in processed_lines:
            conn.execute(
                """INSERT INTO inventory_count_lines
                   (count_id, item_id, system_qty, counted_qty, unit_cost, variance_value)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (count_id, p['item_id'], p['system_qty'], p['counted_qty'],
                 p['unit_cost'], p['variance_value'])
            )

        cur = conn.execute("SELECT COUNT(*)+1 as n FROM stock_transactions WHERE transaction_type='COUNT_ADJUST'")
        n = cur.fetchone()['n']
        txn_no = f"ADJ-TXN-{datetime.now().year}-{n:06d}"

        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, from_warehouse_id, reference_type,
                reference_id, reference_no, status, notes, created_by)
               VALUES (?, 'COUNT_ADJUST', ?, ?, ?, 'QUICK_ADJUST', ?, ?, 'POSTED', ?, ?)""",
            (txn_no, adj_date, warehouse_id, warehouse_id,
             count_id, quick_no, full_notes, user_id)
        )
        txn_id = cur.lastrowid

        for i, p in enumerate(processed_lines, start=1):
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, 1, ?, ?, ?, '')""",
                (txn_id, i, p['item_id'], p['variance_qty'], p['unit_cost'], p['variance_value'])
            )

            cur = conn.execute(
                "SELECT id FROM stock_balances WHERE warehouse_id=? AND item_id=? AND batch_no=''",
                (warehouse_id, p['item_id'])
            )
            if cur.fetchone():
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity = quantity + ?,
                           total_value = total_value + ?,
                           last_updated = CURRENT_TIMESTAMP
                       WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                    (p['variance_qty'], p['variance_value'], warehouse_id, p['item_id'])
                )
            else:
                new_qty = max(0, p['variance_qty'])
                new_val = max(0, p['variance_value'])
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    """INSERT INTO stock_balances
                       (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                       VALUES (?, ?, '', ?, ?, ?)""",
                    (warehouse_id, p['item_id'], new_qty, new_avg, new_val)
                )

            try:
                _cost_method = get_cost_method(p['item_id'])
                if _cost_method == 'FIFO':
                    if adj_type == 'SHORTAGE':
                        _qty = abs(p['variance_qty'])
                        _res = valuation_service.calculate(
                            conn, warehouse_id, p['item_id'], _qty, 'FIFO'
                        )
                        valuation_service.consume_layers(
                            conn, _res.get('consumed_layers', [])
                        )
                    else:
                        _qty = p['variance_qty']
                        conn.execute("""
                            INSERT INTO cost_layers
                            (warehouse_id, item_id, batch_no, receipt_date,
                             original_qty, remaining_qty, unit_cost)
                            VALUES (?, ?, '', ?, ?, ?, ?)
                        """, (
                            warehouse_id, p['item_id'], adj_date,
                            _qty, _qty, p['unit_cost']
                        ))
            except Exception as e:
                print(f"WARN: count layers failed for item {p['item_id']}: {e}")

        conn.execute(
            """UPDATE stock_transactions SET
                 total_qty = (SELECT COALESCE(SUM(quantity),0) FROM stock_transaction_lines WHERE transaction_id=?),
                 total_value = (SELECT COALESCE(SUM(total_cost),0) FROM stock_transaction_lines WHERE transaction_id=?)
               WHERE id=?""",
            (txn_id, txn_id, txn_id)
        )

        cur = conn.execute("SELECT COUNT(*)+1 as n FROM journal_entries")
        jn = cur.fetchone()['n']
        entry_no = f"JE-{datetime.now().year}-{jn:06d}"

        user_id = get_user_id()
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no,
                description, status, total_debit, total_credit, created_by)
               VALUES (?, ?, 'QUICK_ADJUST', ?, ?, ?, 'POSTED', 0, 0, ?)""",
            (entry_no, adj_date, count_id, quick_no,
             f"تسوية {type_ar} - {reason_ar} - {quick_no}", user_id)
        )

        je_id = cur.lastrowid

        line_no = 1
        total_debit = 0
        total_credit = 0

        by_type = {}
        for p in processed_lines:
            key = p['item_type']
            by_type.setdefault(key, 0)
            by_type[key] += p['variance_value']

        for item_type, val in by_type.items():
            if val == 0:
                continue
            inv_acc = _get_inventory_account(item_type)
            abs_val = abs(val)

            if val > 0:
                conn.execute(
                    """INSERT INTO journal_entry_lines
                       (journal_entry_id, line_no, account_code, description,
                        debit_amount, credit_amount)
                       VALUES (?, ?, ?, ?, ?, 0)""",
                    (je_id, line_no, inv_acc, f'زيادة مخزون - {type_ar}', abs_val)
                )
                total_debit += abs_val
                line_no += 1

                conn.execute(
                    """INSERT INTO journal_entry_lines
                       (journal_entry_id, line_no, account_code, description,
                        debit_amount, credit_amount)
                       VALUES (?, ?, '4231', ?, 0, ?)""",
                    (je_id, line_no, f'إيرادات زيادة مخزنية - {reason_ar}', abs_val)
                )
                total_credit += abs_val
                line_no += 1
            else:
                conn.execute(
                    """INSERT INTO journal_entry_lines
                       (journal_entry_id, line_no, account_code, description,
                        debit_amount, credit_amount)
                       VALUES (?, ?, '5563', ?, ?, 0)""",
                    (je_id, line_no, f'عجز مخزون - {reason_ar}', abs_val)
                )
                total_debit += abs_val
                line_no += 1

                conn.execute(
                    """INSERT INTO journal_entry_lines
                       (journal_entry_id, line_no, account_code, description,
                        debit_amount, credit_amount)
                       VALUES (?, ?, ?, ?, 0, ?)""",
                    (je_id, line_no, inv_acc, f'نقص مخزون - {type_ar}', abs_val)
                )
                total_credit += abs_val
                line_no += 1

        conn.execute(
            "UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
            (total_debit, total_credit, je_id)
        )

        conn.execute(
            "UPDATE inventory_counts SET status='POSTED', journal_entry_id=? WHERE id=?",
            (je_id, count_id)
        )
        conn.execute(
            "UPDATE stock_transactions SET journal_entry_id=? WHERE id=?",
            (je_id, txn_id)
        )

    return jsonify({
        'success': True,
        'message': f'تم تسجيل التسوية {quick_no}',
        'data': {
            'count_id': count_id,
            'count_no': quick_no,
            'transaction_id': txn_id,
            'transaction_no': txn_no,
            'journal_entry_id': je_id,
            'entry_no': entry_no,
            'total_value': total_value,
            'adjustment_type': adj_type,
            'reason': reason,
            'reason_ar': reason_ar
        }
    }), 201


@count_bp.route('/adjustments', methods=['GET'])
def list_adjustments():
    """قائمة التسويات السريعة فقط (QUICK)"""
    warehouse_id = request.args.get('warehouse_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    sql = """
        SELECT ic.*, w.name_ar as warehouse_name, je.entry_no,
               (SELECT COALESCE(SUM(ABS(l.variance_value)),0)
                FROM inventory_count_lines l WHERE l.count_id = ic.id) as total_value
        FROM inventory_counts ic
        LEFT JOIN warehouses w ON ic.warehouse_id = w.id
        LEFT JOIN journal_entries je ON ic.journal_entry_id = je.id
        WHERE ic.count_type = 'QUICK'
    """
    params = []

    if warehouse_id:
        sql += " AND ic.warehouse_id = ?"
        params.append(int(warehouse_id))
    if date_from:
        sql += " AND ic.count_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND ic.count_date <= ?"
        params.append(date_to)

    sql += " ORDER BY ic.id DESC LIMIT 200"

    rows = db.query(sql, tuple(params))
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@count_bp.route('/adjustments/<int:aid>', methods=['GET'])
def get_adjustment(aid):
    """تفاصيل تسوية سريعة"""
    row = db.query(
        """SELECT ic.*, w.name_ar as warehouse_name, je.entry_no
           FROM inventory_counts ic
           LEFT JOIN warehouses w ON ic.warehouse_id = w.id
           LEFT JOIN journal_entries je ON ic.journal_entry_id = je.id
           WHERE ic.id=? AND ic.count_type='QUICK'""",
        (aid,), one=True
    )
    if not row:
        return jsonify({'success': False, 'message': 'غير موجودة'}), 404

    lines = db.query(
        """SELECT l.*, i.name_ar as item_name, i.code as item_code
           FROM inventory_count_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.count_id=?""",
        (aid,)
    )
    row['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(row)})