from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

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
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT w.code as warehouse_code, w.name_ar as warehouse_name,
                   i.code as item_code, i.name_ar as item_name, i.item_type,
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
    """تقرير حركات الإضافة (استلام)."""
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
    """تقرير حركات الصرف."""
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
    """تقرير التحويلات."""
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
    """تقرير الجرد."""
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
                   i.code as item_code, i.name_ar as item_name
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
    """كارت الصنف - كل الحركات على صنف معين."""
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'success': False, 'message': 'item_id مطلوب'}), 400
    cond, vals = ['l.item_id = ?', "t.status='POSTED'"], [item_id]
    if request.args.get('date_from'):
        cond.append('t.transaction_date >= ?')
        vals.append(request.args.get('date_from'))
    if request.args.get('date_to'):
        cond.append('t.transaction_date <= ?')
        vals.append(request.args.get('date_to'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT t.id, t.transaction_no, t.transaction_type, t.transaction_date,
                   l.quantity, l.base_quantity, l.unit_cost, l.total_cost,
                   wf.name_ar as from_warehouse, wt.name_ar as to_warehouse
            FROM stock_transactions t
            JOIN stock_transaction_lines l ON t.id = l.transaction_id
            LEFT JOIN warehouses wf ON t.from_warehouse_id = wf.id
            LEFT JOIN warehouses wt ON t.to_warehouse_id = wt.id
            WHERE {where}
            ORDER BY t.transaction_date, t.id""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@report_bp.route('/low-stock', methods=['GET'])
def low_stock():
    rows = db.query(
        """SELECT i.code, i.name_ar, i.reorder_level,
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
                  je.total_debit, je.total_credit, je.status,
                  jel.account_code, jel.debit_amount, jel.credit_amount
           FROM journal_entries je
           JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
           ORDER BY je.id DESC, jel.line_no
           LIMIT 1000"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})
