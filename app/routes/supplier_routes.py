from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

supplier_bp = Blueprint('suppliers', __name__)


@supplier_bp.route('/', methods=['GET'])
def list_suppliers():
    search = request.args.get('search', '')
    conditions, values = ["1=1"], []
    if search:
        conditions.append("(code LIKE ? OR name_ar LIKE ?)")
        values += [f'%{search}%', f'%{search}%']
    where = ' AND '.join(conditions)
    rows = db.query(
        f"SELECT * FROM suppliers WHERE {where} ORDER BY code",
        values
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@supplier_bp.route('/<int:sid>', methods=['GET'])
def get_supplier(sid):
    row = db.query("SELECT * FROM suppliers WHERE id=?", (sid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'المورد غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@supplier_bp.route('/', methods=['POST'])
def create_supplier():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        sid = db.execute(
            """INSERT INTO suppliers 
               (code, name_ar, name_en, phone, email, address, tax_number, 
                account_code, payment_terms, notes, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (d['code'], d['name_ar'], d.get('name_en'),
             d.get('phone'), d.get('email'), d.get('address'),
             d.get('tax_number'), d.get('account_code', '2211'),
             d.get('payment_terms', 30), d.get('notes'))
        )
        return jsonify({'success': True, 'data': {'id': sid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@supplier_bp.route('/<int:sid>', methods=['PUT'])
def update_supplier(sid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'phone', 'email', 'address',
              'tax_number', 'account_code', 'payment_terms', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(sid)
    db.execute(f"UPDATE suppliers SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@supplier_bp.route('/<int:sid>', methods=['DELETE'])
def delete_supplier(sid):
    try:
        db.execute("DELETE FROM suppliers WHERE id=?", (sid,))
        return jsonify({'success': True, 'message': 'تم الحذف'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
