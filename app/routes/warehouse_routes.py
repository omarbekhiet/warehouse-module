from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, enrich_with_user

warehouse_bp = Blueprint('warehouses', __name__)


def generate_next_warehouse_code():
    """يولّد كود المستودع التالي تلقائياً: WH001, WH002, ..."""
    last = db.query(
        "SELECT code FROM warehouses WHERE code LIKE 'WH%' ORDER BY id DESC LIMIT 1",
        one=True
    )
    if not last:
        return "WH001"
    try:
        num = int(last['code'].replace('WH', '').strip())
        return f"WH{num + 1:03d}"
    except:
        n = db.query('SELECT COUNT(*) as n FROM warehouses')[0]['n']
        return f"WH{n + 1:03d}"


@warehouse_bp.route('/', methods=['GET'])
def list_warehouses():
    rows = db.query("SELECT * FROM warehouses ORDER BY code")
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@warehouse_bp.route('/next-code', methods=['GET'])
def next_code():
    """يرجع الكود التالي للمعاينة"""
    return jsonify({'success': True, 'data': {'code': generate_next_warehouse_code()}})


@warehouse_bp.route('/<int:wid>', methods=['GET'])
def get_warehouse(wid):
    row = db.query("SELECT * FROM warehouses WHERE id=?", (wid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@warehouse_bp.route('/', methods=['POST'])
def create_warehouse():
    d = request.get_json() or {}
    
    # الحقول المطلوبة
    for f in ['name_ar', 'warehouse_type', 'account_code']:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'الحقل {f} مطلوب'}), 400
    
    try:
        # الكود: من المستخدم لو موجود، وإلا تلقائي
        code = d.get('code') or generate_next_warehouse_code()
        
        # التحقق من عدم تكرار الكود
        existing = db.query("SELECT id FROM warehouses WHERE code=?", (code,), one=True)
        if existing:
            return jsonify({'success': False, 'message': f'الكود {code} مستخدم بالفعل'}), 400
        
        wid = db.execute(
            """INSERT INTO warehouses 
               (code, name_ar, name_en, warehouse_type, location, 
                account_code, allow_negative, notes, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, d['name_ar'], d.get('name_en'),
             d['warehouse_type'], d.get('location'),
             d['account_code'], 
             1 if d.get('allow_negative') else 0,
             d.get('notes'),
             1 if d.get('is_active', True) else 0)
        )
        return jsonify({'success': True, 'data': {'id': wid, 'code': code}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@warehouse_bp.route('/<int:wid>', methods=['PUT'])
def update_warehouse(wid):
    d = request.get_json() or {}
    fields, values = [], []
    
    for k in ['name_ar', 'name_en', 'warehouse_type', 'location', 
              'account_code', 'is_active', 'notes']:
        if k in d:
            fields.append(f"{k}=?")
            v = d[k]
            if k == 'is_active':
                v = 1 if v else 0
            values.append(v)
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(wid)
    db.execute(f"UPDATE warehouses SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@warehouse_bp.route('/<int:wid>', methods=['DELETE'])
def delete_warehouse(wid):
    with db.transaction() as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=?",
            (wid,)
        )
        if cur.fetchone()['q'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف مستودع به رصيد'}), 400
        
        cur = conn.execute(
            "SELECT COUNT(*) as n FROM stock_transactions WHERE from_warehouse_id=? OR to_warehouse_id=?",
            (wid, wid)
        )
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