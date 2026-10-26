from flask import Blueprint, request, jsonify, session
from app.database import db
from app.utils import json_safe
import hashlib
import json
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


def _hash(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


# ============================================================
# LOGIN
# ============================================================
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

    db.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))

    token = hashlib.sha256(f"{user['id']}-{user['username']}-{datetime.now().isoformat()}".encode()).hexdigest()

    # Parse permissions
    permissions = None
    if user.get('permissions'):
        try:
            permissions = json.loads(user['permissions'])
        except Exception:
            permissions = None

    # Parse branch_ids
    branch_ids = None
    if user.get('branch_ids'):
        try:
            branch_ids = json.loads(user['branch_ids'])
        except Exception:
            branch_ids = None

    # جلب صلاحيات الدور كـ default
    role_permissions = None
    role_row = db.query("SELECT permissions FROM roles WHERE code=?", (user['role'],), one=True)
    if role_row and role_row['permissions']:
        try:
            role_permissions = json.loads(role_row['permissions'])
        except Exception:
            role_permissions = None

    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'permissions': permissions,
                'role_permissions': role_permissions,
                'branch_ids': branch_ids
            }
        }
    })


# ============================================================
# USERS
# ============================================================
@auth_bp.route('/users', methods=['GET'])
def list_users():
    rows = db.query("""SELECT id, username, full_name, email, role,
                       is_active, last_login, permissions, branch_ids
                       FROM users ORDER BY id""")
    return jsonify({'success': True, 'data': json_safe(rows)})


@auth_bp.route('/users', methods=['POST'])
def create_user():
    d = request.get_json() or {}
    if not d.get('username') or not d.get('password'):
        return jsonify({'success': False, 'message': 'البيانات مطلوبة'}), 400
    try:
        perms = d.get('permissions')
        perms_json = json.dumps(perms, ensure_ascii=False) if perms else None

        branches = d.get('branch_ids')
        branches_json = json.dumps(branches, ensure_ascii=False) if branches else None

        uid = db.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, permissions, branch_ids, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (d['username'], _hash(d['password']), d.get('full_name'),
             d.get('email'), d.get('role', 'VIEWER'), perms_json, branches_json)
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

    if 'permissions' in d:
        perms = d.get('permissions')
        perms_json = json.dumps(perms, ensure_ascii=False) if perms else None
        fields.append("permissions=?")
        values.append(perms_json)

    if 'branch_ids' in d:
        branches = d.get('branch_ids')
        branches_json = json.dumps(branches, ensure_ascii=False) if branches else None
        fields.append("branch_ids=?")
        values.append(branches_json)

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


# ============================================================
# ROLES
# ============================================================
@auth_bp.route('/roles', methods=['GET'])
def list_roles():
    rows = db.query("""SELECT id, code, name_ar, name_en, color, permissions, is_system, created_at
                       FROM roles ORDER BY id""")
    return jsonify({'success': True, 'data': json_safe(rows)})


@auth_bp.route('/roles', methods=['POST'])
def create_role():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        perms = d.get('permissions')
        perms_json = json.dumps(perms, ensure_ascii=False) if perms else None

        rid = db.execute(
            """INSERT INTO roles (code, name_ar, name_en, color, permissions, is_system)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (d['code'].upper(), d['name_ar'], d.get('name_en'),
             d.get('color', '#64748b'), perms_json)
        )
        return jsonify({'success': True, 'data': {'id': rid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@auth_bp.route('/roles/<int:rid>', methods=['PUT'])
def update_role(rid):
    d = request.get_json() or {}
    fields, values = [], []

    for k in ['name_ar', 'name_en', 'color']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])

    if 'permissions' in d:
        perms = d.get('permissions')
        perms_json = json.dumps(perms, ensure_ascii=False) if perms else None
        fields.append("permissions=?")
        values.append(perms_json)

    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400

    values.append(rid)
    db.execute(f"UPDATE roles SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@auth_bp.route('/roles/<int:rid>', methods=['DELETE'])
def delete_role(rid):
    role = db.query("SELECT is_system FROM roles WHERE id=?", (rid,), one=True)
    if not role:
        return jsonify({'success': False, 'message': 'الدور غير موجود'}), 404
    if role['is_system']:
        return jsonify({'success': False, 'message': 'لا يمكن حذف دور نظام'}), 400
    db.execute("DELETE FROM roles WHERE id=?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})