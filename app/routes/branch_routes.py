from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, enrich_with_user

branch_bp = Blueprint('branches', __name__)


@branch_bp.route('/', methods=['GET'])
def list_branches():
    rows = db.query("SELECT * FROM branches ORDER BY code")
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@branch_bp.route('/<int:bid>', methods=['GET'])
def get_branch(bid):
    row = db.query("SELECT * FROM branches WHERE id=?", (bid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'الفرع غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@branch_bp.route('/', methods=['POST'])
def create_branch():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        bid = db.execute("""
            INSERT INTO branches (code, name_ar, name_en, address, phone, manager_name, is_active, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (d['code'], d['name_ar'], d.get('name_en'),
              d.get('address'), d.get('phone'), d.get('manager_name'),
              1, d.get('notes')))
        return jsonify({'success': True, 'data': {'id': bid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@branch_bp.route('/<int:bid>', methods=['PUT'])
def update_branch(bid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'address', 'phone',
              'manager_name', 'is_active', 'notes']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(bid)
    db.execute(f"UPDATE branches SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@branch_bp.route('/<int:bid>', methods=['DELETE'])
def delete_branch(bid):
    db.execute("DELETE FROM branches WHERE id=?", (bid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
