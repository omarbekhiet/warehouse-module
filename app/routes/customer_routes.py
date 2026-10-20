from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, enrich_with_user

customer_bp = Blueprint('customers', __name__)


@customer_bp.route('/', methods=['GET'])
def list_customers():
    search = request.args.get('search', '')
    conditions, values = ["1=1"], []
    if search:
        conditions.append("(code LIKE ? OR name_ar LIKE ?)")
        values += [f'%{search}%', f'%{search}%']
    where = ' AND '.join(conditions)
    rows = db.query(f"SELECT * FROM customers WHERE {where} ORDER BY code", values)
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@customer_bp.route('/<int:cid>', methods=['GET'])
def get_customer(cid):
    row = db.query("SELECT * FROM customers WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'العميل غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@customer_bp.route('/', methods=['POST'])
def create_customer():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        cid = db.execute(
            """INSERT INTO customers 
               (code, name_ar, name_en, phone, email, address, tax_number,
                commercial_register, company_type, legal_form, tax_office, national_id,
                account_code, credit_limit, payment_terms, notes, group_id, credit_days, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (d['code'], d['name_ar'], d.get('name_en'),
             d.get('phone'), d.get('email'), d.get('address'),
             d.get('tax_number'), d.get('commercial_register'),
             d.get('company_type'), d.get('legal_form'), d.get('tax_office'), d.get('national_id'),
             d.get('account_code', '1221001'),
             d.get('credit_limit', 0),
             d.get('payment_terms', 30), d.get('notes'),
             d.get('group_id'), d.get('credit_days'))
        )
        return jsonify({'success': True, 'data': {'id': cid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@customer_bp.route('/<int:cid>', methods=['PUT'])
def update_customer(cid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'phone', 'email', 'address',
              'tax_number', 'commercial_register', 'company_type', 'legal_form',
              'tax_office', 'national_id',
              'account_code', 'credit_limit', 'payment_terms', 'credit_days',
              'notes', 'is_active', 'group_id']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(cid)
    db.execute(f"UPDATE customers SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@customer_bp.route('/<int:cid>', methods=['DELETE'])
def delete_customer(cid):
    try:
        db.execute("DELETE FROM customers WHERE id=?", (cid,))
        return jsonify({'success': True, 'message': 'تم الحذف'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
