from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

pm_bp = Blueprint('payment_methods', __name__)


@pm_bp.route('/', methods=['GET'])
def list_methods():
    rows = db.query("""
        SELECT pm.*, a.name_ar as account_name
        FROM payment_methods pm
        LEFT JOIN accounts a ON pm.account_code = a.code
        WHERE pm.is_active = 1
        ORDER BY pm.id
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@pm_bp.route('/all', methods=['GET'])
def list_all_methods():
    """كل الطرق (نشطة وموقفة)"""
    rows = db.query("""
        SELECT pm.*, a.name_ar as account_name
        FROM payment_methods pm
        LEFT JOIN accounts a ON pm.account_code = a.code
        ORDER BY pm.id
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@pm_bp.route('/<int:mid>', methods=['GET'])
def get_method(mid):
    row = db.query("SELECT * FROM payment_methods WHERE id=?", (mid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@pm_bp.route('/', methods=['POST'])
def create_method():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar') or not d.get('account_code'):
        return jsonify({'success': False, 'message': 'الحقول مطلوبة'}), 400
    
    # التحقق من الحساب موجود في الدليل
    acc = db.query("SELECT code FROM accounts WHERE code=?", (d['account_code'],), one=True)
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب غير موجود في الدليل'}), 400
    
    try:
        mid = db.execute("""
            INSERT INTO payment_methods 
            (code, name_ar, name_en, account_code, requires_clearing, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            d['code'], d['name_ar'], d.get('name_en'),
            d['account_code'], d.get('requires_clearing', 0)
        ))
        return jsonify({'success': True, 'data': {'id': mid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@pm_bp.route('/<int:mid>', methods=['PUT'])
def update_method(mid):
    d = request.get_json() or {}
    fields, values = [], []
    
    for k in ['name_ar', 'name_en', 'account_code', 'requires_clearing', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(mid)
    db.execute(f"UPDATE payment_methods SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@pm_bp.route('/<int:mid>', methods=['DELETE'])
def delete_method(mid):
    # تحقق من الاستخدام
    with db.get_connection() as conn:
        cur = conn.execute("""
            SELECT COUNT(*) as n FROM supplier_payments WHERE payment_method = 
            (SELECT code FROM payment_methods WHERE id=?)
        """, (mid,))
        if cur.fetchone()['n'] > 0:
            return jsonify({'success': False, 'message': 'الطريقة مستخدمة — يجب إيقافها بدلاً من حذفها'}), 400
        
        conn.execute("DELETE FROM payment_methods WHERE id=?", (mid,))
        conn.commit()
    
    return jsonify({'success': True, 'message': 'تم الحذف'})