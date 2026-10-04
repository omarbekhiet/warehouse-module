from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

uom_bp = Blueprint('uom', __name__)


@uom_bp.route('/', methods=['GET'])
def list_uom():
    rows = db.query("SELECT * FROM units_of_measure ORDER BY id")
    return jsonify({'success': True, 'data': json_safe(rows)})


@uom_bp.route('/<int:uid>', methods=['GET'])
def get_uom(uid):
    row = db.query("SELECT * FROM units_of_measure WHERE id=?", (uid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@uom_bp.route('/', methods=['POST'])
def create_uom():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        uid = db.execute(
            "INSERT INTO units_of_measure (code, name_ar, name_en, is_active) VALUES (?, ?, ?, 1)",
            (d['code'], d['name_ar'], d.get('name_en', ''))
        )
        return jsonify({'success': True, 'data': {'id': uid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@uom_bp.route('/<int:uid>', methods=['PUT'])
def update_uom(uid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(uid)
    db.execute(f"UPDATE units_of_measure SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@uom_bp.route('/<int:uid>', methods=['DELETE'])
def delete_uom(uid):
    # Check usage
    with db.transaction() as conn:
        cur = conn.execute("SELECT COUNT(*) as n FROM items WHERE base_uom_id=? OR medium_uom_id=? OR major_uom_id=?", (uid, uid, uid))
        if cur.fetchone()['n'] > 0:
            return jsonify({'success': False, 'message': 'الوحدة مستخدمة في أصناف'}), 400
        conn.execute("DELETE FROM units_of_measure WHERE id=?", (uid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
