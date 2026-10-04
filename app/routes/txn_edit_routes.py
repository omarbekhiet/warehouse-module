from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service

txn_edit_bp = Blueprint('txn_edit', __name__)


# ============ DELETE TRANSACTION (only DRAFT) ============
@txn_edit_bp.route('/<int:tid>', methods=['DELETE'])
def delete_transaction(tid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM stock_transactions WHERE id=?", (tid,))
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الحركة غير موجودة'}), 404
        if txn['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'لا يمكن حذف حركة مرحّلة'}), 400

        conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id=?", (tid,))
        conn.execute("DELETE FROM stock_transactions WHERE id=?", (tid,))

    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============ GET FULL TRANSACTION WITH LINES ============
@txn_edit_bp.route('/<int:tid>', methods=['GET'])
def get_transaction(tid):
    with db.get_connection() as conn:
        cur = conn.execute("SELECT * FROM stock_transactions WHERE id=?", (tid,))
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        txn = dict(txn)

        cur = conn.execute(
            """SELECT l.*, i.name_ar as item_name, i.code as item_code,
                      i.base_uom_id, u.name_ar as uom_name, u.code as uom_code
               FROM stock_transaction_lines l
               JOIN items i ON l.item_id = i.id
               LEFT JOIN units_of_measure u ON l.uom_id = u.id
               WHERE l.transaction_id=? ORDER BY l.line_no""",
            (tid,)
        )
        txn['lines'] = [dict(r) for r in cur.fetchall()]

    return jsonify({'success': True, 'data': json_safe(txn)})


# ============ UPDATE DRAFT TRANSACTION ============
@txn_edit_bp.route('/<int:tid>', methods=['PUT'])
def update_transaction(tid):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM stock_transactions WHERE id=?", (tid,))
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if txn['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'لا يمكن تعديل حركة مرحّلة'}), 400

        # Update header
        conn.execute(
            """UPDATE stock_transactions
               SET transaction_date=?, reference_no=?, notes=?
               WHERE id=?""",
            (d.get('transaction_date', txn['transaction_date']),
             d.get('reference_no'), d.get('notes'), tid)
        )

        # Replace lines if provided
        if d.get('lines'):
            conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id=?", (tid,))
            total_qty = to_decimal(0)
            total_val = to_decimal(0)
            for i, line in enumerate(d['lines'], start=1):
                qty = to_decimal(line['quantity'])
                uc = to_decimal(line.get('unit_cost', 0))
                tc = round_decimal(qty * uc)
                conn.execute(
                    """INSERT INTO stock_transaction_lines
                       (transaction_id, line_no, item_id, uom_id, quantity,
                        unit_cost, total_cost, batch_no)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (tid, i, line['item_id'], line.get('uom_id', 1),
                     float(qty), float(uc), float(tc),
                     line.get('batch_no') or '')
                )
                total_qty += qty
                total_val += tc

            conn.execute(
                "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
                (float(total_qty), float(round_decimal(total_val)), tid)
            )

    return jsonify({'success': True, 'message': 'تم التحديث'})


# ============ ITEM UPDATE ============
@txn_edit_bp.route('/item/<int:iid>', methods=['PUT'])
def update_item(iid):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT id FROM items WHERE id=?", (iid,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

        fields, values = [], []
        for k in ['name_ar','name_en','category_id','item_type','base_uom_id',
                  'cost_method','inventory_account','cost_account','reorder_level',
                  'is_active','barcode','notes']:
            if k in d:
                fields.append(f"{k}=?")
                values.append(d[k])
        if not fields:
            return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
        values.append(iid)
        conn.execute(f"UPDATE items SET {','.join(fields)} WHERE id=?", values)

    return jsonify({'success': True, 'message': 'تم تحديث الصنف'})


# ============ ITEM DELETE ============
@txn_edit_bp.route('/item/<int:iid>', methods=['DELETE'])
def delete_item(iid):
    with db.transaction() as conn:
        # Check if item has stock
        cur = conn.execute("SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE item_id=?", (iid,))
        if cur.fetchone()['q'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف صنف له رصيد'}), 400

        conn.execute("DELETE FROM uom_conversions WHERE item_id=?", (iid,))
        conn.execute("DELETE FROM items WHERE id=?", (iid))

    return jsonify({'success': True, 'message': 'تم حذف الصنف'})


# ============ WAREHOUSE UPDATE/DELETE ============
@txn_edit_bp.route('/warehouse/<int:wid>', methods=['PUT'])
def update_warehouse(wid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar','name_en','warehouse_type','location','account_code','is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(wid)
    db.execute(f"UPDATE warehouses SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True})


@txn_edit_bp.route('/warehouse/<int:wid>', methods=['DELETE'])
def delete_warehouse(wid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=?", (wid,))
        if cur.fetchone()['q'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف مستودع به رصيد'}), 400
        conn.execute("DELETE FROM warehouses WHERE id=?", (wid,))
    return jsonify({'success': True})


# ============ COUNT UPDATE/DELETE ============
@txn_edit_bp.route('/count/<int:cid>', methods=['DELETE'])
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
