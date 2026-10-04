from flask import Blueprint, request, jsonify, session
from app.database import db
from app.utils import json_safe
import hashlib
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


def _hash(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


@auth_bp.route('/login', methods=['POST'])
def login():
    d = request.get_json() or {}
    username = (d.get('username') or '').strip()
    password = (d.get('password') or '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'اسم المستخدم وكلمة المرور مطلوبان'}), 400

    user = db.query("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user or user['password_hash'] != _hash(password):
        return jsonify({'success': False, 'message': 'بيانات الدخول غير صحيحة'}), 401

    if not user['is_active']:
        return jsonify({'success': False, 'message': 'الحساب موقوف'}), 403

    # Update last_login
    db.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))

    # Simple token (in production use JWT)
    token = hashlib.sha256(f"{user['id']}-{user['username']}-{datetime.now().isoformat()}".encode()).hexdigest()

    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role']
            }
        }
    })


@auth_bp.route('/users', methods=['GET'])
def list_users():
    rows = db.query("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id")
    return jsonify({'success': True, 'data': json_safe(rows)})


@auth_bp.route('/users', methods=['POST'])
def create_user():
    d = request.get_json() or {}
    if not d.get('username') or not d.get('password'):
        return jsonify({'success': False, 'message': 'البيانات مطلوبة'}), 400
    try:
        uid = db.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, is_active)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (d['username'], _hash(d['password']), d.get('full_name'),
             d.get('email'), d.get('role', 'USER'))
        )
        return jsonify({'success': True, 'data': {'id': uid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@auth_bp.route('/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['full_name', 'email', 'role', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if d.get('password'):
        fields.append("password_hash=?")
        values.append(_hash(d['password']))
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(uid)
    db.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@auth_bp.route('/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    if uid == 1:
        return jsonify({'success': False, 'message': 'لا يمكن حذف المدير الرئيسي'}), 400
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
