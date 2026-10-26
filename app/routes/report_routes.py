from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal, enrich_with_user

report_bp = Blueprint('reports', __name__)


@report_bp.route('/stock-balance', methods=['GET'])
def stock_balance():
    cond, vals = ['sb.quantity != 0'], []
    if request.args.get('warehouse_id'):
        cond.append('sb.warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))
    if request.args.get('item_id'):
        cond.append('sb.item_id = ?')
        vals.append(request.args.get('item_id'))
    if request.args.get('operating_type'):
        cond.append('i.operating_type = ?')
        vals.append(request.args.get('operating_type'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT w.code as warehouse_code, w.name_ar as warehouse_name,
                   i.code as item_code, i.name_ar as item_name, i.item_type,
                   i.operating_type,
                   sb.batch_no, sb.quantity, sb.average_cost, sb.total_value,
                   sb.last_updated
            FROM stock_balances sb
            JOIN warehouses w ON sb.warehouse_id = w.id
            JOIN items i ON sb.item_id = i.id
            WHERE {where}
            ORDER BY w.code, i.code""",
        vals
    )
    total_value = sum(float(r['total_value'] or 0) for r in rows)
    return jsonify({'success': True, 'data': json_safe(rows), 'total_value': total_value})


@report_bp.route('/receipts', methods=['GET'])
def receipts_report():
    cond, vals = ["t.transaction_type='RECEIPT'", "t.status='POSTED'"], []
    if request.args.get('date_from'):
        cond.append('t.transaction_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('t.transaction_date <= ?')
        vals.append(request.args.get('date_to'))
    if request.args.get('warehouse_id'):
        cond.append('t.to_warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))
    if request.args.get('item_id'):
        cond.append('l.item_id = ?')
        vals.append(request.args.get('item_id'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT t.id, t.transaction_no, t.transaction_date,
                   w.name_ar as warehouse_name,
                   i.code as item_code, i.name_ar as item_name,
                   i.operating_type,
                   l.quantity, l.base_quantity, l.unit_cost, l.total_cost,
                   t.reference_no, t.reference_type
            FROM stock_transactions t
            JOIN stock_transaction_lines l ON t.id = l.transaction_id
            JOIN items i ON l.item_id = i.id
            JOIN warehouses w ON t.to_warehouse_id = w.id
            WHERE {where}
            ORDER BY t.transaction_date DESC, t.id DESC""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/issues', methods=['GET'])
def issues_report():
    cond, vals = ["t.transaction_type='ISSUE'", "t.status='POSTED'"], []
    if request.args.get('date_from'):
        cond.append('t.transaction_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('t.transaction_date <= ?')
        vals.append(request.args.get('date_to'))
    if request.args.get('warehouse_id'):
        cond.append('t.from_warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))
    if request.args.get('item_id'):
        cond.append('l.item_id = ?')
        vals.append(request.args.get('item_id'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT t.id, t.transaction_no, t.transaction_date,
                   w.name_ar as warehouse_name,
                   i.code as item_code, i.name_ar as item_name,
                   i.operating_type,
                   l.quantity, l.base_quantity, l.unit_cost, l.total_cost,
                   t.reference_no, t.reference_type
            FROM stock_transactions t
            JOIN stock_transaction_lines l ON t.id = l.transaction_id
            JOIN items i ON l.item_id = i.id
            JOIN warehouses w ON t.from_warehouse_id = w.id
            WHERE {where}
            ORDER BY t.transaction_date DESC, t.id DESC""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/transfers', methods=['GET'])
def transfers_report():
    cond, vals = ["t.transaction_type='TRANSFER'", "t.status='POSTED'"], []
    if request.args.get('date_from'):
        cond.append('t.transaction_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('t.transaction_date <= ?')
        vals.append(request.args.get('date_to'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT t.id, t.transaction_no, t.transaction_date,
                   wf.name_ar as from_warehouse, wt.name_ar as to_warehouse,
                   i.code as item_code, i.name_ar as item_name,
                   i.operating_type,
                   l.quantity, l.base_quantity, l.unit_cost, l.total_cost
            FROM stock_transactions t
            JOIN stock_transaction_lines l ON t.id = l.transaction_id
            JOIN items i ON l.item_id = i.id
            JOIN warehouses wf ON t.from_warehouse_id = wf.id
            JOIN warehouses wt ON t.to_warehouse_id = wt.id
            WHERE {where}
            ORDER BY t.transaction_date DESC, t.id DESC""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/counts', methods=['GET'])
def counts_report():
    cond, vals = ["1=1"], []
    if request.args.get('date_from'):
        cond.append('ic.count_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('ic.count_date <= ?')
        vals.append(request.args.get('date_to'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT ic.id, ic.count_no, ic.count_date, ic.count_type, ic.status,
                   w.name_ar as warehouse_name,
                   l.system_qty, l.counted_qty,
                   (l.counted_qty - l.system_qty) as variance_qty,
                   l.unit_cost, l.variance_value,
                   i.code as item_code, i.name_ar as item_name,
                   i.operating_type
            FROM inventory_counts ic
            JOIN inventory_count_lines l ON ic.id = l.count_id
            JOIN items i ON l.item_id = i.id
            JOIN warehouses w ON ic.warehouse_id = w.id
            WHERE {where}
            ORDER BY ic.count_date DESC, ic.id DESC""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/item-card', methods=['GET'])
def item_card():
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'success': False, 'message': 'item_id ط¸â€¦ط·آ·ط¸â€‍ط¸ث†ط·آ¨'}), 400

    cond, vals = ['l.item_id = ?', "t.status='POSTED'"], [item_id]

    if request.args.get('date_from'):
        cond.append('t.transaction_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('t.transaction_date <= ?')
        vals.append(request.args.get('date_to'))
    if request.args.get('warehouse_id'):
        cond.append('(t.from_warehouse_id = ? OR t.to_warehouse_id = ?)')
        vals.append(request.args.get('warehouse_id'))
        vals.append(request.args.get('warehouse_id'))
    if request.args.get('transaction_type'):
        cond.append('t.transaction_type = ?')
        vals.append(request.args.get('transaction_type'))

    where = ' AND '.join(cond)

    # ط·آ¬ط¸ظ¹ط·آ¨ ط·آ¨ط¸ظ¹ط·آ§ط¸â€ ط·آ§ط·ع¾ ط·آ§ط¸â€‍ط·آµط¸â€ ط¸ظ¾
    item = db.query(
        "SELECT id, code, name_ar, item_type, operating_type, base_uom_id FROM items WHERE id=?",
        (item_id,), one=True
    )
    if not item:
        return jsonify({'success': False, 'message': 'ط·آ§ط¸â€‍ط·آµط¸â€ ط¸ظ¾ ط·ط›ط¸ظ¹ط·آ± ط¸â€¦ط¸ث†ط·آ¬ط¸ث†ط·آ¯'}), 404

    # ط·آ§ط¸â€‍ط·آ±ط·آµط¸ظ¹ط·آ¯ ط·آ§ط¸â€‍ط·آ§ط¸ظ¾ط·ع¾ط·ع¾ط·آ§ط·آ­ط¸ظ¹ (ط¸â€ڑط·آ¨ط¸â€‍ date_from ط¸â€‍ط¸ث† ط¸â€¦ط¸ث†ط·آ¬ط¸ث†ط·آ¯)
    opening_qty = 0
    if request.args.get('date_from'):
        opening_row = db.query(
            """SELECT COALESCE(SUM(l.quantity), 0) as qty
               FROM stock_transactions t
               JOIN stock_transaction_lines l ON t.id = l.transaction_id
               WHERE l.item_id = ? AND t.status='POSTED' AND t.transaction_date < ?""",
            (item_id, request.args.get('date_from')), one=True
        )
        opening_qty = float(opening_row['qty'] or 0) if opening_row else 0

    # ط·آ§ط¸â€‍ط·آ­ط·آ±ط¸ئ’ط·آ§ط·ع¾
    rows = db.query(
        f"""SELECT t.id, t.transaction_no, t.transaction_type, t.transaction_date,
                   t.notes,
                   l.quantity, l.base_quantity, l.unit_cost, l.total_cost,
                   t.from_warehouse_id, t.to_warehouse_id,
                   wf.code as from_wh_code, wf.name_ar as from_warehouse,
                   wt.code as to_wh_code, wt.name_ar as to_warehouse
            FROM stock_transactions t
            JOIN stock_transaction_lines l ON t.id = l.transaction_id
            LEFT JOIN warehouses wf ON t.from_warehouse_id = wf.id
            LEFT JOIN warehouses wt ON t.to_warehouse_id = wt.id
            WHERE {where}
            ORDER BY t.transaction_date, t.id""",
        vals
    )

    # ط·آ§ط¸â€‍ط·آ±ط·آµط¸ظ¹ط·آ¯ ط·آ§ط¸â€‍ط·آ­ط·آ§ط¸â€‍ط¸ظ¹
    current_qty = opening_qty + sum(float(r['quantity'] or 0) for r in rows)

    return jsonify({
        'success': True,
        'data': json_safe(rows),
        'item': json_safe(dict(item)),
        'opening_qty': opening_qty,
        'current_qty': current_qty
    })
@report_bp.route('/low-stock', methods=['GET'])
def low_stock():
    rows = db.query(
        """SELECT i.code, i.name_ar, i.reorder_level,
                  i.operating_type,
                  COALESCE(SUM(sb.quantity),0) as total_qty
           FROM items i
           LEFT JOIN stock_balances sb ON i.id = sb.item_id
           WHERE i.is_active=1 AND i.reorder_level > 0
           GROUP BY i.id
           HAVING total_qty < i.reorder_level
           ORDER BY (i.reorder_level - total_qty) DESC"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/valuation', methods=['GET'])
def valuation():
    rows = db.query(
        """SELECT i.item_type, COUNT(DISTINCT i.id) as item_count,
                  COALESCE(SUM(sb.quantity),0) as total_qty,
                  COALESCE(SUM(sb.total_value),0) as total_value
           FROM items i
           LEFT JOIN stock_balances sb ON i.id = sb.item_id
           GROUP BY i.item_type"""
    )
    
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/journal-entries', methods=['GET'])
def journal_entries():
    rows = db.query(
        """SELECT je.id, je.entry_no, je.entry_date, je.reference_no, je.description,
                  je.total_debit, je.total_credit, je.status, je.created_by,
                  jel.account_code, jel.debit_amount, jel.credit_amount
           FROM journal_entries je
           JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
           ORDER BY je.id DESC, jel.line_no
           LIMIT 1000"""
    )
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})
    

@report_bp.route('/inventory-by-warehouse', methods=['GET'])
def inventory_by_warehouse():
    """ط·ع¾ط¸â€ڑط·آ±ط¸ظ¹ط·آ± ط·آ§ط¸â€‍ط¸â€¦ط·آ®ط·آ²ط¸ث†ط¸â€  ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط¸â€¦ط·آ³ط·ع¾ط¸ث†ط·آ¯ط·آ¹ ط¸â€¦ط·آ¹ ط·آ§ط¸â€‍ط·ع¾ط·آµط¸â€ ط¸ظ¹ط¸ظ¾."""
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                w.name_ar as warehouse_name,
                COALESCE(i.operating_type, 'OPERATING') as operating_type,
                COUNT(DISTINCT i.id) as item_count,
                COALESCE(SUM(sb.quantity), 0) as total_qty,
                COALESCE(SUM(sb.total_value), 0) as total_value
            FROM warehouses w
            LEFT JOIN stock_balances sb ON w.id = sb.warehouse_id
            LEFT JOIN items i ON sb.item_id = i.id
            WHERE sb.quantity > 0
            GROUP BY w.id, i.operating_type
            ORDER BY w.name_ar, i.operating_type
        """).fetchall()
    
    by_warehouse = {}
    for r in rows:
        wh = r['warehouse_name']
        if wh not in by_warehouse:
            by_warehouse[wh] = {
                'warehouse': wh,
                'items': [],
                'total_value': 0
            }
        op = r['operating_type'] or 'OPERATING'
        val = float(r['total_value'] or 0)
        by_warehouse[wh]['items'].append({
            'operating_type': op,
            'item_count': r['item_count'],
            'total_qty': float(r['total_qty'] or 0),
            'total_value': val
        })
        by_warehouse[wh]['total_value'] += val
    

    return jsonify({
        'success': True,
        'data': list(by_warehouse.values())
    })
@report_bp.route('/adjustments', methods=['GET'])
def adjustments_report():
    """
    ط·ع¾ط¸â€ڑط·آ±ط¸ظ¹ط·آ± ط·آ´ط·آ§ط¸â€¦ط¸â€‍ ط¸â€‍ط¸â€‍ط·ع¾ط·آ³ط¸ث†ط¸ظ¹ط·آ§ط·ع¾ ط·آ§ط¸â€‍ط¸â€¦ط·آ®ط·آ²ط¸â€ ط¸ظ¹ط·آ©
    - ط¸ظ¾ط¸â€‍ط·ع¾ط·آ±ط·آ©: ط·ع¾ط·آ§ط·آ±ط¸ظ¹ط·آ® / ط¸â€¦ط·آ³ط·ع¾ط¸ث†ط·آ¯ط·آ¹ / ط¸â€ ط¸ث†ط·آ¹ / ط·آ³ط·آ¨ط·آ¨
    - ط·آ¥ط·آ¬ط¸â€¦ط·آ§ط¸â€‍ط¸ظ¹ط·آ§ط·ع¾: ط·آ¹ط·آ¯ط·آ¯ط·إ’ ط·آ¹ط·آ¬ط·آ²ط·إ’ ط·آ²ط¸ظ¹ط·آ§ط·آ¯ط·آ©ط·إ’ ط·آµط·آ§ط¸ظ¾ط¸ظ¹
    - ط·ع¾ط·آ¬ط¸â€¦ط¸ظ¹ط·آ¹ط·آ§ط·ع¾: ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨ + ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط¸â€¦ط·آ³ط·ع¾ط¸ث†ط·آ¯ط·آ¹
    """
    cond = ["ic.count_type = 'QUICK'"]
    vals = []

    if request.args.get('date_from'):
        cond.append('ic.count_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('ic.count_date <= ?')
        vals.append(request.args.get('date_to'))
    if request.args.get('warehouse_id'):
        cond.append('ic.warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))

    where = ' AND '.join(cond)

    # ===== ط·آ§ط¸â€‍ط·ع¾ط·آ³ط¸ث†ط¸ظ¹ط·آ§ط·ع¾ =====
    rows = db.query(
        f"""SELECT ic.id, ic.count_no, ic.count_date, ic.notes, ic.status,
                   ic.journal_entry_id,
                   w.name_ar as warehouse_name,
                   je.entry_no,
                   COALESCE((SELECT SUM(ABS(l.variance_value))
                             FROM inventory_count_lines l
                             WHERE l.count_id = ic.id), 0) as total_value,
                   COALESCE((SELECT SUM(CASE WHEN l.variance_value < 0
                                             THEN ABS(l.variance_value) ELSE 0 END)
                             FROM inventory_count_lines l
                             WHERE l.count_id = ic.id), 0) as shortage_value,
                   COALESCE((SELECT SUM(CASE WHEN l.variance_value > 0
                                             THEN l.variance_value ELSE 0 END)
                             FROM inventory_count_lines l
                             WHERE l.count_id = ic.id), 0) as surplus_value,
                   (SELECT COUNT(*) FROM inventory_count_lines l
                    WHERE l.count_id = ic.id) as line_count
            FROM inventory_counts ic
            LEFT JOIN warehouses w ON ic.warehouse_id = w.id
            LEFT JOIN journal_entries je ON ic.journal_entry_id = je.id
            WHERE {where}
            ORDER BY ic.count_date DESC, ic.id DESC""",
        tuple(vals)
    )

    # ===== ط¸ظ¾ط¸â€‍ط·ع¾ط·آ±ط·آ© ط·آ¥ط·آ¶ط·آ§ط¸ظ¾ط¸ظ¹ط·آ© (ط¸â€ ط¸ث†ط·آ¹ + ط·آ³ط·آ¨ط·آ¨) ط·آ¨ط·آ¹ط·آ¯ ط·آ§ط¸â€‍ط·آ¬ط¸â€‍ط·آ¨ =====
    filter_type = request.args.get('adjustment_type')  # SHORTAGE / SURPLUS
    filter_reason = request.args.get('reason')         # DAMAGE / BREAKAGE ...

    filtered = []
    for r in rows:
        notes = r.get('notes') or ''

        # ط¸â€ ط¸ث†ط·آ¹ ط·آ§ط¸â€‍ط·ع¾ط·آ³ط¸ث†ط¸ظ¹ط·آ©
        is_shortage = '[ط·آ¹ط·آ¬ط·آ²]' in notes
        is_surplus = '[ط·آ²ط¸ظ¹ط·آ§ط·آ¯ط·آ©]' in notes

        if filter_type == 'SHORTAGE' and not is_shortage:
            continue
        if filter_type == 'SURPLUS' and not is_surplus:
            continue

        # ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨
        if filter_reason:
            if f'ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨: {filter_reason}' not in notes:
                # ط¸â€ ط·آ¨ط·آ­ط·آ« ط·آ¨ط·آ§ط¸â€‍ط·آ§ط·آ³ط¸â€¦ ط·آ§ط¸â€‍ط·آ¹ط·آ±ط·آ¨ط¸ظ¹ ط¸ئ’ط¸â€¦ط·آ§ط¸â€ 
                continue

        # ط·آ§ط·آ³ط·ع¾ط·آ®ط·آ±ط·آ§ط·آ¬ ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨
        reason_ar = 'أ¢â‚¬â€‌'
        m = None
        import re as _re
        m = _re.search(r'ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨:\s*([^|]+)', notes)
        if m:
            reason_ar = m.group(1).strip()

        r['adjustment_type'] = 'SHORTAGE' if is_shortage else 'SURPLUS'
        r['reason_ar'] = reason_ar
        filtered.append(r)

    rows = filtered

    # ===== ط·آ§ط¸â€‍ط·آ¥ط·آ¬ط¸â€¦ط·آ§ط¸â€‍ط¸ظ¹ط·آ§ط·ع¾ =====
    total_count = len(rows)
    total_shortage = sum(float(r['shortage_value'] or 0) for r in rows)
    total_surplus = sum(float(r['surplus_value'] or 0) for r in rows)
    net_value = total_surplus - total_shortage

    # ===== ط·ع¾ط·آ¬ط¸â€¦ط¸ظ¹ط·آ¹ ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط·آ³ط·آ¨ط·آ¨ =====
    by_reason = {}
    for r in rows:
        key = r['reason_ar']
        by_reason.setdefault(key, {
            'reason': key,
            'count': 0,
            'shortage': 0.0,
            'surplus': 0.0
        })
        by_reason[key]['count'] += 1
        by_reason[key]['shortage'] += float(r['shortage_value'] or 0)
        by_reason[key]['surplus'] += float(r['surplus_value'] or 0)

    # ===== ط·ع¾ط·آ¬ط¸â€¦ط¸ظ¹ط·آ¹ ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط¸â€¦ط·آ³ط·ع¾ط¸ث†ط·آ¯ط·آ¹ =====
    by_warehouse = {}
    for r in rows:
        key = r['warehouse_name'] or 'أ¢â‚¬â€‌'
        by_warehouse.setdefault(key, {
            'warehouse': key,
            'count': 0,
            'shortage': 0.0,
            'surplus': 0.0
        })
        by_warehouse[key]['count'] += 1
        by_warehouse[key]['shortage'] += float(r['shortage_value'] or 0)
        by_warehouse[key]['surplus'] += float(r['surplus_value'] or 0)

        return jsonify({
        'success': True,
        'data': json_safe(rows),
        'totals': {
            'count': total_count,
            'shortage': total_shortage,
            'surplus': total_surplus,
            'net': net_value
        },
        'by_reason': list(by_reason.values()),
        'by_warehouse': list(by_warehouse.values())
    })

@report_bp.route('/price-comparison', methods=['GET'])
def price_comparison():
    """
    ط¸â€¦ط¸â€ڑط·آ§ط·آ±ط¸â€ ط·آ© ط·آ£ط·آ³ط·آ¹ط·آ§ط·آ± ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ±ط·آ¯ط¸ظ¹ط¸â€  ط¸â€‍ط¸ئ’ط¸â€‍ ط·آµط¸â€ ط¸ظ¾
    Filters: item_id, supplier_id, date_from, date_to
    """
    cond = ["pi.status='POSTED'"]
    vals = []

    if request.args.get('item_id'):
        cond.append('pil.item_id = ?')
        vals.append(request.args.get('item_id'))
    if request.args.get('supplier_id'):
        cond.append('pi.supplier_id = ?')
        vals.append(request.args.get('supplier_id'))
    if request.args.get('date_from'):
        cond.append('pi.invoice_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('pi.invoice_date <= ?')
        vals.append(request.args.get('date_to'))

    where = ' AND '.join(cond)

    rows = db.query(
        f"""SELECT
                pil.item_id,
                i.code as item_code,
                i.name_ar as item_name,
                i.base_uom_id,
                pi.supplier_id,
                s.code as supplier_code,
                s.name_ar as supplier_name,
                COUNT(*) as invoice_count,
                MIN(pil.unit_price) as min_price,
                MAX(pil.unit_price) as max_price,
                AVG(pil.unit_price) as avg_price,
                SUM(pil.base_quantity) as total_qty
            FROM purchase_invoice_lines pil
            JOIN purchase_invoices pi ON pil.invoice_id = pi.id
            JOIN items i ON pil.item_id = i.id
            JOIN suppliers s ON pi.supplier_id = s.id
            WHERE {where}
            GROUP BY pil.item_id, pi.supplier_id
            ORDER BY i.code, MIN(pil.unit_price)""",
        vals
    )

    # ط·ع¾ط·آ¬ط¸â€¦ط¸ظ¹ط·آ¹ ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط·آµط¸â€ ط¸ظ¾
    items_map = {}
    for r in rows:
        item_id = r['item_id']
        if item_id not in items_map:
            items_map[item_id] = {
                'item_id': item_id,
                'item_code': r['item_code'],
                'item_name': r['item_name'],
                'base_uom_id': r['base_uom_id'],
                'suppliers': []
            }
        items_map[item_id]['suppliers'].append({
            'supplier_id': r['supplier_id'],
            'supplier_code': r['supplier_code'],
            'supplier_name': r['supplier_name'],
            'invoice_count': r['invoice_count'],
            'min_price': float(r['min_price'] or 0),
            'max_price': float(r['max_price'] or 0),
            'avg_price': float(r['avg_price'] or 0),
            'total_qty': float(r['total_qty'] or 0)
        })

    # ط¸â€‍ط¸ئ’ط¸â€‍ ط·آµط¸â€ ط¸ظ¾: ط·ع¾ط·آ±ط·ع¾ط¸ظ¹ط·آ¨ ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ±ط·آ¯ط¸ظ¹ط¸â€  + ط·آ£ط¸ظ¾ط·آ¶ط¸â€‍ ط¸â€¦ط¸ث†ط·آ±ط·آ¯
    for item in items_map.values():
        item['suppliers'].sort(key=lambda x: x['min_price'])
        if item['suppliers']:
            best = item['suppliers'][0]
            worst = item['suppliers'][-1]
            item['best_supplier'] = best
            item['worst_supplier'] = worst
            item['price_diff'] = worst['min_price'] - best['min_price']
            item['price_diff_pct'] = (
                (item['price_diff'] / best['min_price'] * 100)
                if best['min_price'] > 0 else 0
            )

    data = list(items_map.values())

    # ط·آ¥ط·آ¬ط¸â€¦ط·آ§ط¸â€‍ط¸ظ¹ط·آ§ط·ع¾
    total_items = len(data)
    total_savings = sum(
        item.get('price_diff', 0) * item.get('best_supplier', {}).get('total_qty', 0)
        for item in data
    )

    return jsonify({
        'success': True,
        'data': data,
        'totals': {
            'items_count': total_items,
            'total_savings': round(total_savings, 2)
        }
    })

@report_bp.route('/supplier-rating', methods=['GET'])
def supplier_rating():
    """
    ط·ع¾ط¸â€ڑط¸ظ¹ط¸ظ¹ط¸â€¦ ط·ع¾ط¸â€‍ط¸â€ڑط·آ§ط·آ¦ط¸ظ¹ ط¸â€‍ط¸â€‍ط¸â€¦ط¸ث†ط·آ±ط·آ¯ط¸ظ¹ط¸â€  ط·آ¨ط¸â€ ط·آ§ط·طŒط¸â€¹ ط·آ¹ط¸â€‍ط¸â€°:
    - ط·آ§ط¸â€‍ط·آ³ط·آ¹ط·آ± (30%)
    - ط·آ§ط¸â€‍ط·آ§ط¸â€‍ط·ع¾ط·آ²ط·آ§ط¸â€¦ ط·آ¨ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ§ط·آ¹ط¸ظ¹ط·آ¯ (25%)
    - ط·آ¹ط·آ¯ط·آ¯ ط·آ§ط¸â€‍ط¸ظ¾ط¸ث†ط·آ§ط·ع¾ط¸ظ¹ط·آ± (20%)
    - ط·آ§ط¸â€‍ط¸â€¦ط·آ±ط·ع¾ط·آ¬ط·آ¹ط·آ§ط·ع¾ (15%)
    - ط·آ§ط¸â€‍ط·آ§ط·آ³ط·ع¾ط¸â€¦ط·آ±ط·آ§ط·آ±ط¸ظ¹ط·آ© (10%)
    """
    from datetime import datetime

    # 1. ط·آ¬ط¸â€‍ط·آ¨ ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ±ط·آ¯ط¸ظ¹ط¸â€ 
    suppliers = db.query("""
        SELECT id, code, name_ar, name_en, phone, payment_terms
        FROM suppliers
        WHERE is_active = 1
        ORDER BY name_ar
    """)

    result = []

    for sup in suppliers:
        sid = sup['id']

        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        # 1. ط·آ¹ط·آ¯ط·آ¯ ط·آ§ط¸â€‍ط¸ظ¾ط¸ث†ط·آ§ط·ع¾ط¸ظ¹ط·آ±
        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        inv_row = db.query("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(total_amount), 0) as total_value,
                   MIN(invoice_date) as first_inv,
                   MAX(invoice_date) as last_inv
            FROM purchase_invoices
            WHERE supplier_id = ? AND status = 'POSTED'
        """, (sid,), one=True)

        invoice_count = int(inv_row['cnt'] or 0)
        total_value = float(inv_row['total_value'] or 0)
        first_inv = inv_row['first_inv']
        last_inv = inv_row['last_inv']

        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        # 2. ط·آ¹ط·آ¯ط·آ¯ ط·آ£ط¸ث†ط·آ§ط¸â€¦ط·آ± ط·آ§ط¸â€‍ط·آ´ط·آ±ط·آ§ط·طŒ + ط·آ§ط¸â€‍ط·آ§ط¸â€‍ط·ع¾ط·آ²ط·آ§ط¸â€¦
        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        po_row = db.query("""
            SELECT
                COUNT(*) as total_po,
                SUM(CASE WHEN status IN ('COMPLETED') THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status IN ('APPROVED', 'PARTIAL') THEN 1 ELSE 0 END) as pending
            FROM purchase_orders
            WHERE supplier_id = ?
        """, (sid,), one=True)

        total_po = int(po_row['total_po'] or 0)
        completed_po = int(po_row['completed'] or 0)
        pending_po = int(po_row['pending'] or 0)

        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        # 3. ط·آ¹ط·آ¯ط·آ¯ ط·آ§ط¸â€‍ط¸â€¦ط·آ±ط·ع¾ط·آ¬ط·آ¹ط·آ§ط·ع¾
        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        ret_row = db.query("""
            SELECT COUNT(*) as cnt
            FROM purchase_returns
            WHERE supplier_id = ? AND status = 'POSTED'
        """, (sid,), one=True)

        return_count = int(ret_row['cnt'] or 0)

        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        # 4. ط¸â€¦ط·ع¾ط¸ث†ط·آ³ط·آ· ط·آ£ط·آ³ط·آ¹ط·آ§ط·آ± ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ±ط·آ¯
        # أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬أ¢â€‌â‚¬
        price_row = db.query("""
            SELECT AVG(pil.unit_price) as avg_price
            FROM purchase_invoice_lines pil
            JOIN purchase_invoices pi ON pil.invoice_id = pi.id
            WHERE pi.supplier_id = ? AND pi.status = 'POSTED'
        """, (sid,), one=True)

        avg_price = float(price_row['avg_price'] or 0)

        result.append({
            'supplier_id': sid,
            'code': sup['code'],
            'name': sup['name_ar'],
            'phone': sup['phone'],
            'payment_terms': sup['payment_terms'],
            'invoice_count': invoice_count,
            'total_value': total_value,
            'first_invoice': first_inv,
            'last_invoice': last_inv,
            'total_po': total_po,
            'completed_po': completed_po,
            'pending_po': pending_po,
            'return_count': return_count,
            'avg_price': avg_price,
        })

    # أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯
    # ط·آ­ط·آ³ط·آ§ط·آ¨ ط·آ§ط¸â€‍ط¸â€ ط¸â€ڑط·آ§ط·آ· (0-100) ط¸â€‍ط¸ئ’ط¸â€‍ ط¸â€¦ط¸ث†ط·آ±ط·آ¯
    # أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯أ¢â€¢ع¯

    # ط¸â€ ط·آ­ط·ع¾ط·آ§ط·آ¬ ط¸â€ڑط¸ظ¹ط¸â€¦ ط¸â€¦ط·آ±ط·آ¬ط·آ¹ط¸ظ¹ط·آ©
    max_invoices = max((r['invoice_count'] for r in result), default=1) or 1
    max_value = max((r['total_value'] for r in result), default=1) or 1
    max_po = max((r['total_po'] for r in result), default=1) or 1
    min_price = min((r['avg_price'] for r in result if r['avg_price'] > 0), default=0)

    for r in result:
        # 1. ط·آ§ط¸â€‍ط·آ³ط·آ¹ط·آ± (30%) أ¢â‚¬â€‌ ط¸ئ’ط¸â€‍ ط¸â€¦ط·آ§ ط¸â€ڑط¸â€‍ط·إ’ ط¸ئ’ط¸â€‍ ط¸â€¦ط·آ§ ط·آ²ط·آ§ط·آ¯ط·ع¾ ط·آ§ط¸â€‍ط¸â€ ط¸â€ڑط·آ§ط·آ·
        if r['avg_price'] > 0 and min_price > 0:
            price_score = min(100, (min_price / r['avg_price']) * 100)
        else:
            price_score = 50
        r['price_score'] = round(price_score, 1)

        # 2. ط·آ§ط¸â€‍ط·آ§ط¸â€‍ط·ع¾ط·آ²ط·آ§ط¸â€¦ ط·آ¨ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ§ط·آ¹ط¸ظ¹ط·آ¯ (25%) أ¢â‚¬â€‌ ط¸â€ ط·آ³ط·آ¨ط·آ© ط·آ§ط¸â€‍ط·آ£ط¸ث†ط·آ§ط¸â€¦ط·آ± ط·آ§ط¸â€‍ط¸â€¦ط¸ئ’ط·ع¾ط¸â€¦ط¸â€‍ط·آ©
        if r['total_po'] > 0:
            commitment_score = (r['completed_po'] / r['total_po']) * 100
        else:
            commitment_score = 50
        r['commitment_score'] = round(commitment_score, 1)

        # 3. ط·آ¹ط·آ¯ط·آ¯ ط·آ§ط¸â€‍ط¸ظ¾ط¸ث†ط·آ§ط·ع¾ط¸ظ¹ط·آ± (20%)
        invoice_score = min(100, (r['invoice_count'] / max_invoices) * 100)
        r['invoice_score'] = round(invoice_score, 1)

        # 4. ط·آ§ط¸â€‍ط¸â€¦ط·آ±ط·ع¾ط·آ¬ط·آ¹ط·آ§ط·ع¾ (15%) أ¢â‚¬â€‌ ط¸ئ’ط¸â€‍ ط¸â€¦ط·آ§ ط¸â€ڑط¸â€‍ط¸â€کط·ع¾ط·إ’ ط¸ئ’ط¸â€‍ ط¸â€¦ط·آ§ ط·آ²ط·آ§ط·آ¯ط·ع¾ ط·آ§ط¸â€‍ط¸â€ ط¸â€ڑط·آ§ط·آ·
        if r['invoice_count'] > 0:
            return_ratio = r['return_count'] / r['invoice_count']
            return_score = max(0, 100 - (return_ratio * 100))
        else:
            return_score = 50
        r['return_score'] = round(return_score, 1)

        # 5. ط·آ§ط¸â€‍ط·آ§ط·آ³ط·ع¾ط¸â€¦ط·آ±ط·آ§ط·آ±ط¸ظ¹ط·آ© (10%) أ¢â‚¬â€‌ ط·آ¹ط·آ¯ط·آ¯ ط·آ§ط¸â€‍ط·آ£ط·آ´ط¸â€،ط·آ± ط·آ¨ط¸ظ¹ط¸â€  ط·آ£ط¸ث†ط¸â€‍ ط¸ث†ط·آ¢ط·آ®ط·آ± ط¸ظ¾ط·آ§ط·ع¾ط¸ث†ط·آ±ط·آ©
        if r['first_invoice'] and r['last_invoice']:
            try:
                from datetime import datetime as dt
                d1 = dt.strptime(r['first_invoice'], '%Y-%m-%d')
                d2 = dt.strptime(r['last_invoice'], '%Y-%m-%d')
                days = (d2 - d1).days
                months = max(1, days // 30)
                continuity_score = min(100, months * 10)  # ط¸ئ’ط¸â€‍ ط·آ´ط¸â€،ط·آ± = 10 ط¸â€ ط¸â€ڑط·آ§ط·آ·
            except:
                continuity_score = 50
        else:
            continuity_score = 0
        r['continuity_score'] = round(continuity_score, 1)

        # ط·آ§ط¸â€‍ط¸â€¦ط·آ¬ط¸â€¦ط¸ث†ط·آ¹ (0-100)
        total_score = (
            r['price_score'] * 0.30 +
            r['commitment_score'] * 0.25 +
            r['invoice_score'] * 0.20 +
            r['return_score'] * 0.15 +
            r['continuity_score'] * 0.10
        )
        r['total_score'] = round(total_score, 1)

        # ط·آ§ط¸â€‍ط·ع¾ط·آµط¸â€ ط¸ظ¹ط¸ظ¾ (ط¸â€ ط·آ¬ط¸ث†ط¸â€¦)
        if total_score >= 80:
            r['grade'] = 'A+'
            r['grade_color'] = '#16a34a'
        elif total_score >= 70:
            r['grade'] = 'A'
            r['grade_color'] = '#22c55e'
        elif total_score >= 60:
            r['grade'] = 'B'
            r['grade_color'] = '#eab308'
        elif total_score >= 50:
            r['grade'] = 'C'
            r['grade_color'] = '#f59e0b'
        else:
            r['grade'] = 'D'
            r['grade_color'] = '#dc2626'

    # ط·ع¾ط·آ±ط·ع¾ط¸ظ¹ط·آ¨ ط·آ­ط·آ³ط·آ¨ ط·آ§ط¸â€‍ط¸â€ ط¸â€ڑط·آ§ط·آ·
    result.sort(key=lambda x: x['total_score'], reverse=True)

    return jsonify({
        'success': True,
        'data': json_safe(result)
    })

@report_bp.route('/batches', methods=['GET'])
def list_batches():
    """
    ط¸â€ڑط·آ§ط·آ¦ط¸â€¦ط·آ© ط¸ئ’ط¸â€‍ ط·آ§ط¸â€‍ط·آ¯ط¸ظ¾ط·آ¹ط·آ§ط·ع¾ ط·آ§ط¸â€‍ط¸â€¦ط¸ث†ط·آ¬ط¸ث†ط·آ¯ط·آ© ط·آ­ط·آ§ط¸â€‍ط¸ظ¹ط·آ§ط¸â€¹
    Filters: item_id, warehouse_id, expiring_days
    """
    cond = ["sb.quantity > 0", "sb.batch_no != ''"]
    vals = []

    if request.args.get('item_id'):
        cond.append('sb.item_id = ?')
        vals.append(request.args.get('item_id'))
    if request.args.get('warehouse_id'):
        cond.append('sb.warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))

    where = ' AND '.join(cond)

    rows = db.query(
        f"""SELECT
                sb.batch_no,
                sb.item_id,
                i.code as item_code,
                i.name_ar as item_name,
                sb.warehouse_id,
                w.name_ar as warehouse_name,
                sb.quantity,
                sb.average_cost,
                sb.total_value,
                sb.expiry_date,
                CASE
                    WHEN sb.expiry_date IS NOT NULL AND sb.expiry_date != ''
                    THEN CAST(julianday(sb.expiry_date) - julianday('now') AS INTEGER)
                    ELSE NULL
                END as days_to_expiry
            FROM stock_balances sb
            JOIN items i ON sb.item_id = i.id
            JOIN warehouses w ON sb.warehouse_id = w.id
            WHERE {where}
            ORDER BY
                CASE WHEN sb.expiry_date IS NULL OR sb.expiry_date = '' THEN 1 ELSE 0 END,
                sb.expiry_date ASC,
                i.code""",
        tuple(vals)
    )

    # ط¸ظ¾ط¸â€‍ط·ع¾ط·آ±ط·آ© ط·آ­ط·آ³ط·آ¨ expiring_days
    expiring_days = request.args.get('expiring_days')
    if expiring_days:
        try:
            days_limit = int(expiring_days)
            rows = [r for r in rows
                    if r['days_to_expiry'] is not None and r['days_to_expiry'] <= days_limit]
        except ValueError:
            pass

    return jsonify({
        'success': True,
        'data': json_safe(rows)
    })


@report_bp.route('/expiring', methods=['GET'])
def expiring_items():
    """
    ط·آ§ط¸â€‍ط·آ£ط·آµط¸â€ ط·آ§ط¸ظ¾ ط·آ§ط¸â€‍ط¸â€ڑط·آ±ط¸ظ¹ط·آ¨ط·آ© ط¸â€¦ط¸â€  ط·آ§ط¸â€‍ط·آ§ط¸â€ ط·ع¾ط¸â€،ط·آ§ط·طŒ
    Filters: days (ط·آ§ط¸â€‍ط·آ§ط¸ظ¾ط·ع¾ط·آ±ط·آ§ط·آ¶ط¸ظ¹ 30), warehouse_id
    """
    days = request.args.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30

    cond = [
        "sb.quantity > 0",
        "sb.expiry_date IS NOT NULL",
        "sb.expiry_date != ''",
        "julianday(sb.expiry_date) - julianday('now') <= ?",
        "julianday(sb.expiry_date) - julianday('now') >= 0"
    ]
    vals = [days]

    if request.args.get('warehouse_id'):
        cond.append('sb.warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))

    where = ' AND '.join(cond)

    rows = db.query(
        f"""SELECT
                sb.batch_no,
                sb.item_id,
                i.code as item_code,
                i.name_ar as item_name,
                w.name_ar as warehouse_name,
                sb.quantity,
                sb.average_cost,
                sb.total_value,
                sb.expiry_date,
                CAST(julianday(sb.expiry_date) - julianday('now') AS INTEGER) as days_to_expiry
            FROM stock_balances sb
            JOIN items i ON sb.item_id = i.id
            JOIN warehouses w ON sb.warehouse_id = w.id
            WHERE {where}
            ORDER BY sb.expiry_date ASC""",
        tuple(vals)
    )

    return jsonify({
        'success': True,
        'data': json_safe(rows),
        'totals': {
            'count': len(rows),
            'total_value': sum(float(r['total_value'] or 0) for r in rows)
        }
    })


@report_bp.route('/expired', methods=['GET'])
def expired_items():
    """ط·آ§ط¸â€‍ط·آ£ط·آµط¸â€ ط·آ§ط¸ظ¾ ط·آ§ط¸â€‍ط¸â€¦ط¸â€ ط·ع¾ط¸â€،ط¸ظ¹ط·آ©"""
    cond = [
        "sb.quantity > 0",
        "sb.expiry_date IS NOT NULL",
        "sb.expiry_date != ''",
        "julianday(sb.expiry_date) - julianday('now') < 0"
    ]
    vals = []

    if request.args.get('warehouse_id'):
        cond.append('sb.warehouse_id = ?')
        vals.append(request.args.get('warehouse_id'))

    where = ' AND '.join(cond)

    rows = db.query(
        f"""SELECT
                sb.batch_no,
                sb.item_id,
                i.code as item_code,
                i.name_ar as item_name,
                w.name_ar as warehouse_name,
                sb.quantity,
                sb.total_value,
                sb.expiry_date,
                CAST(julianday('now') - julianday(sb.expiry_date) AS INTEGER) as days_expired
            FROM stock_balances sb
            JOIN items i ON sb.item_id = i.id
            JOIN warehouses w ON sb.warehouse_id = w.id
            WHERE {where}
            ORDER BY sb.expiry_date ASC""",
        tuple(vals)
    )

    return jsonify({
        'success': True,
        'data': json_safe(rows)
    })


# ============================================================
# ط¸â€¦ط¸ظ¹ط·آ²ط·آ§ط¸â€  ط·آ§ط¸â€‍ط¸â€¦ط·آ±ط·آ§ط·آ¬ط·آ¹ط·آ© (Trial Balance)
# ============================================================
@report_bp.route('/financial-reports/cash-flow', methods=['GET'])
@report_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    level_filter = request.args.get('level')
    stmt_filter = request.args.get('stmt')

    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level, financial_statement FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                
                acc_dict[code] = {
                    'code': code, 'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl, 'financial_statement': a['financial_statement'],
                    'opening_balance': 0.0, 'period_debit': 0.0, 'period_credit': 0.0
                }

            if from_date:
                q_open = """SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                             FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                             WHERE je.status = 'POSTED' AND je.entry_date < ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)"""
                for r in conn.execute(q_open, (from_date,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['opening_balance'] = float(r['d']) - float(r['c'])

            cond, vals = ["je.status = 'POSTED'", "jl.account_code IS NOT NULL"], []
            if from_date:
                cond.append("je.entry_date >= ?"); vals.append(from_date)
            if to_date:
                cond.append("je.entry_date <= ?"); vals.append(to_date)
            where = " AND ".join(cond)

            q_period = f"""SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                            FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                            WHERE {where} GROUP BY CAST(jl.account_code AS TEXT)"""
            for r in conn.execute(q_period, tuple(vals)).fetchall():
                c = str(r['acc_code']).strip()
                if c in acc_dict:
                    acc_dict[c]['period_debit'] = float(r['d'])
                    acc_dict[c]['period_credit'] = float(r['c'])

            # ط·آ§ط¸â€‍ط·ع¾ط·آ¬ط¸â€¦ط¸ظ¹ط·آ¹ (Roll-up)
            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['opening_balance'] += node['opening_balance']
                    acc_dict[parent]['period_debit'] += node['period_debit']
                    acc_dict[parent]['period_credit'] += node['period_credit']

            # ط·آ¨ط¸â€ ط·آ§ط·طŒ ط·آ§ط¸â€‍ط¸â€ ط·ع¾ط¸ظ¹ط·آ¬ط·آ© ط¸â€¦ط·آ¹ ط·آ§ط¸â€‍ط¸ظ¾ط¸â€‍ط·ع¾ط·آ±ط·آ©
            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                
                
                
                
                
                result.append(node)

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



# ============================================================
# Balance Sheet Route (Added Automatically)
# ============================================================


# ============================================================
# Balance Sheet Route (Advanced Logic based on Chart of Accounts)
# ============================================================


@report_bp.route('/financial-reports/balance-sheet', methods=['GET'])
def balance_sheet_report():
    as_of = request.args.get('as_of')
    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level, financial_statement FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                
                acc_dict[code] = {
                    'code': code, 
                    'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl, 
                    'financial_statement': a['financial_statement'],
                    'balance': 0.0
                }

            if as_of:
                q = """SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                       FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                       WHERE je.status = 'POSTED' AND je.entry_date <= ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)"""
                for r in conn.execute(q, (as_of,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['balance'] = float(r['bal'])

            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['balance'] += node['balance']

            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                if code.startswith('2') or code.startswith('8'):
                    node['balance'] = -node['balance']
                result.append(node)

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@report_bp.route('/audit/journal-entries', methods=['GET'])
def audit_journal_entries():
    as_of = request.args.get('as_of')
    try:
        with db.get_connection() as conn:
            q = """
                SELECT je.id, je.entry_date, je.description, jl.account_code, a.name_ar, a.level, 
                       jl.debit_amount, jl.credit_amount
                FROM journal_entries je
                JOIN journal_entry_lines jl ON je.id = jl.journal_entry_id
                LEFT JOIN accounts a ON jl.account_code = a.code
                WHERE je.status = 'POSTED'
            """
            params = []
            if as_of:
                q += " AND je.entry_date <= ?"
                params.append(as_of)
            q += " ORDER BY je.entry_date DESC, je.id DESC"
            
            rows = conn.execute(q, params).fetchall()
            result = [dict(r) for r in rows]
            return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500








@report_bp.route('/cash-flow', methods=['GET'])
def cash_flow_report():
    to_date = request.args.get('to_date')
    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                acc_dict[code] = {'code': code, 'name': a['name_ar'], 'parent': str(a['parent_code']).strip() if a['parent_code'] else None, 'level': lvl, 'balance': 0.0}

            if to_date:
                q = '''SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                       FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                       WHERE je.status = 'POSTED' AND je.entry_date <= ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)'''
                params = (to_date,)
            else:
                q = '''SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                       FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                       WHERE je.status = 'POSTED' AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)'''
                params = ()
                
            for r in conn.execute(q, params).fetchall():
                c = str(r['acc_code']).strip()
                if c in acc_dict:
                    acc_dict[c]['balance'] = float(r['bal'])

            total_revenue = 0
            total_expenses = 0
            for code, node in acc_dict.items():
                if code.startswith('4'): total_revenue += abs(node['balance'])
                elif code.startswith('3') or code.startswith('5') or code.startswith('6') or code.startswith('7'):
                    total_expenses += node['balance']
            net_profit = total_revenue - total_expenses

            depreciation = 0
            for code, node in acc_dict.items():
                if code.startswith('531') or 'إهلاك' in node['name']:
                    depreciation += abs(node['balance'])

            receivables = 0
            inventory = 0
            payables = 0
            for code, node in acc_dict.items():
                if code.startswith('122'): receivables += node['balance']
                elif code.startswith('123'): inventory += node['balance']
                elif code.startswith('221'): payables += abs(node['balance'])

            cash_balance = 0
            for code, node in acc_dict.items():
                if code.startswith('121'): cash_balance += node['balance']

            operating_cash_flow = net_profit + depreciation - receivables - inventory + payables
            investing_cash_flow = 0
            financing_cash_flow = 0
            net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow

            result = {
                'net_profit': net_profit,
                'depreciation': depreciation,
                'change_receivables': -receivables,
                'change_inventory': -inventory,
                'change_payables': payables,
                'operating_cash_flow': operating_cash_flow,
                'investing_cash_flow': investing_cash_flow,
                'financing_cash_flow': financing_cash_flow,
                'net_cash_flow': net_cash_flow,
                'opening_cash': cash_balance - net_cash_flow,
                'closing_cash': cash_balance
            }

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500






@report_bp.route('/income-statement', methods=['GET'])
def income_statement_report():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level, pl_group FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                
                acc_dict[code] = {
                    'code': code,
                    'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl,
                    'pl_group': a['pl_group'],
                    'closing_balance': 0.0,
                    'opening_balance': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0
                }

            # 1. الأرصدة الافتتاحية (ما قبل from_date)
            if from_date:
                q_open = """SELECT CAST(jl.account_code AS TEXT) as acc_code, 
                               COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                        FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                        WHERE je.status = 'POSTED' AND je.entry_date < ? AND jl.account_code IS NOT NULL 
                        GROUP BY CAST(jl.account_code AS TEXT)"""
                for r in conn.execute(q_open, (from_date,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['opening_balance'] = float(r['bal'])

            # 2. حركة الفترة (بين from_date و to_date)
            q_period = """SELECT CAST(jl.account_code AS TEXT) as acc_code, 
                           COALESCE(SUM(jl.debit_amount), 0) as debits,
                           COALESCE(SUM(jl.credit_amount), 0) as credits
                    FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                    WHERE je.status = 'POSTED' AND jl.account_code IS NOT NULL"""
            
            params = []
            if from_date:
                q_period += " AND je.entry_date >= ?"
                params.append(from_date)
            if to_date:
                q_period += " AND je.entry_date <= ?"
                params.append(to_date)
            q_period += " GROUP BY CAST(jl.account_code AS TEXT)"
            
            for r in conn.execute(q_period, params).fetchall():
                c = str(r['acc_code']).strip()
                if c in acc_dict:
                    acc_dict[c]['period_debit'] = float(r['debits'])
                    acc_dict[c]['period_credit'] = float(r['credits'])
                    acc_dict[c]['closing_balance'] = acc_dict[c]['opening_balance'] + (float(r['debits']) - float(r['credits']))

            # 3. التجميع للأعلى
            sorted_codes = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_codes:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['closing_balance'] += node['closing_balance']
                    acc_dict[parent]['period_debit'] += node['period_debit']
                    acc_dict[parent]['period_credit'] += node['period_credit']

            # 4. تحويل الإشارات (الإيرادات)
            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                if code.startswith('4'):
                    node['closing_balance'] = -node['closing_balance']
                result.append(node)

            return jsonify({'success': True, 'data': result})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

