from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

warehouse_bp = Blueprint('warehouses', __name__)


@warehouse_bp.route('/', methods=['GET'])
def list_warehouses():
    rows = db.query("SELECT * FROM warehouses ORDER BY code")
    return jsonify({'success': True, 'data': json_safe(rows)})


@warehouse_bp.route('/<int:wid>', methods=['GET'])
def get_warehouse(wid):
    row = db.query("SELECT * FROM warehouses WHERE id=?", (wid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@warehouse_bp.route('/', methods=['POST'])
def create_warehouse():
    d = request.get_json() or {}
    for f in ['code', 'name_ar', 'warehouse_type', 'account_code']:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'الحقل {f} مطلوب'}), 400
    try:
        wid = db.execute(
            """INSERT INTO warehouses (code, name_ar, name_en, warehouse_type,
               location, account_code, allow_negative, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (d['code'], d['name_ar'], d.get('name_en'),
             d['warehouse_type'], d.get('location'),
             d['account_code'], d.get('allow_negative', 0), 1)
        )
        return jsonify({'success': True, 'data': {'id': wid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@warehouse_bp.route('/<int:wid>', methods=['PUT'])
def update_warehouse(wid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'warehouse_type', 'location', 'account_code', 'is_active', 'notes']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(wid)
    db.execute(f"UPDATE warehouses SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@warehouse_bp.route('/<int:wid>', methods=['DELETE'])
def delete_warehouse(wid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=?", (wid,))
        if cur.fetchone()['q'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف مستودع به رصيد'}), 400
        cur = conn.execute("SELECT COUNT(*) as n FROM stock_transactions WHERE from_warehouse_id=? OR to_warehouse_id=?", (wid, wid))
        if cur.fetchone()['n'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف مستودع له حركات'}), 400
        conn.execute("DELETE FROM warehouses WHERE id=?", (wid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@warehouse_bp.route('/<int:wid>/stock', methods=['GET'])
def warehouse_stock(wid):
    rows = db.query(
        """SELECT sb.*, i.code as item_code, i.name_ar as item_name
           FROM stock_balances sb
           JOIN items i ON sb.item_id = i.id
           WHERE sb.warehouse_id=? AND sb.quantity != 0
           ORDER BY i.code""",
        (wid,)
    )
    return jsonify({'success': True, 'data': json_safe(rows)})
