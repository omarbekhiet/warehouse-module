from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

mapping_bp = Blueprint('mapping', __name__)


# ============================================================
# 1. inventory_account_mappings — كل الـ mappings
# ============================================================
@mapping_bp.route('/inventory-mappings', methods=['GET'])
def list_inventory_mappings():
    search = request.args.get('search', '')
    cond, vals = ['1=1'], []
    
    if search:
        cond.append('(transaction_type LIKE ? OR item_type LIKE ? OR debit_account LIKE ? OR credit_account LIKE ? OR description_ar LIKE ?)')
        s = f'%{search}%'
        vals.extend([s, s, s, s, s])
    
    where = ' AND '.join(cond)
    rows = db.query(f"""
        SELECT * FROM inventory_account_mappings
        WHERE {where}
        ORDER BY transaction_type, item_type
    """, vals)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mapping_bp.route('/inventory-mappings/<int:mid>', methods=['PUT'])
def update_inventory_mapping(mid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['transaction_type', 'item_type', 'debit_account', 'credit_account', 
              'description_ar', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(mid)
    db.execute(f"UPDATE inventory_account_mappings SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@mapping_bp.route('/inventory-mappings', methods=['POST'])
def create_inventory_mapping():
    d = request.get_json() or {}
    try:
        mid = db.execute("""
            INSERT INTO inventory_account_mappings 
            (transaction_type, item_type, debit_account, credit_account, description_ar, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (d['transaction_type'], d['item_type'], d['debit_account'], 
              d['credit_account'], d.get('description_ar')))
        return jsonify({'success': True, 'data': {'id': mid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@mapping_bp.route('/inventory-mappings/<int:mid>', methods=['DELETE'])
def delete_inventory_mapping(mid):
    db.execute("DELETE FROM inventory_account_mappings WHERE id=?", (mid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============================================================
# 2. settings الحسابات
# ============================================================
@mapping_bp.route('/settings-accounts', methods=['GET'])
def list_settings_accounts():
    rows = db.query("""
        SELECT key, value, label_ar, category FROM settings
        WHERE key LIKE '%account%'
        ORDER BY category, key
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mapping_bp.route('/settings-accounts/<path:key>', methods=['PUT'])
def update_setting_account(key):
    d = request.get_json() or {}
    value = d.get('value', '')
    if not value:
        return jsonify({'success': False, 'message': 'القيمة مطلوبة'}), 400
    db.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    return jsonify({'success': True, 'message': 'تم التحديث'})


# ============================================================
# 3. العملاء → الحسابات
# ============================================================
@mapping_bp.route('/customers-accounts', methods=['GET'])
def list_customers_accounts():
    search = request.args.get('search', '')
    cond, vals = ['1=1'], []
    
    if search:
        cond.append('(c.code LIKE ? OR c.name_ar LIKE ? OR c.account_code LIKE ? OR a.name_ar LIKE ?)')
        s = f'%{search}%'
        vals.extend([s, s, s, s])
    
    where = ' AND '.join(cond)
    rows = db.query(f"""
        SELECT c.id, c.code, c.name_ar, c.phone, c.account_code,
               a.name_ar as acc_name, a.level as acc_level
        FROM customers c
        LEFT JOIN accounts a ON c.account_code = a.code
        WHERE {where}
        ORDER BY c.code
        LIMIT 200
    """, vals)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mapping_bp.route('/customers-accounts/<int:cid>', methods=['PUT'])
def update_customer_account(cid):
    d = request.get_json() or {}
    acc = d.get('account_code', '')
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب مطلوب'}), 400
    
    # نتأكد إن الحساب موجود
    existing = db.query("SELECT code, name_ar FROM accounts WHERE code=?", (acc,), one=True)
    if not existing:
        return jsonify({'success': False, 'message': 'الحساب مش موجود في الدليل'}), 400
    
    db.execute("UPDATE customers SET account_code=? WHERE id=?", (acc, cid))
    return jsonify({'success': True, 'message': 'تم التحديث', 'acc_name': existing['name_ar']})


# ============================================================
# 4. الموردين → الحسابات
# ============================================================
@mapping_bp.route('/suppliers-accounts', methods=['GET'])
def list_suppliers_accounts():
    search = request.args.get('search', '')
    cond, vals = ['1=1'], []
    
    if search:
        cond.append('(s.code LIKE ? OR s.name_ar LIKE ? OR s.account_code LIKE ? OR a.name_ar LIKE ?)')
        s = f'%{search}%'
        vals.extend([s, s, s, s])
    
    where = ' AND '.join(cond)
    rows = db.query(f"""
        SELECT s.id, s.code, s.name_ar, s.phone, s.account_code,
               a.name_ar as acc_name, a.level as acc_level
        FROM suppliers s
        LEFT JOIN accounts a ON s.account_code = a.code
        WHERE {where}
        ORDER BY s.code
        LIMIT 200
    """, vals)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mapping_bp.route('/suppliers-accounts/<int:sid>', methods=['PUT'])
def update_supplier_account(sid):
    d = request.get_json() or {}
    acc = d.get('account_code', '')
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب مطلوب'}), 400
    
    existing = db.query("SELECT code, name_ar FROM accounts WHERE code=?", (acc,), one=True)
    if not existing:
        return jsonify({'success': False, 'message': 'الحساب مش موجود في الدليل'}), 400
    
    db.execute("UPDATE suppliers SET account_code=? WHERE id=?", (acc, sid))
    return jsonify({'success': True, 'message': 'تم التحديث', 'acc_name': existing['name_ar']})


# ============================================================
# 5. المخازن → الحسابات
# ============================================================
@mapping_bp.route('/warehouses-accounts', methods=['GET'])
def list_warehouses_accounts():
    rows = db.query("""
        SELECT w.id, w.code, w.name_ar, w.account_code,
               a.name_ar as acc_name
        FROM warehouses w
        LEFT JOIN accounts a ON w.account_code = a.code
        ORDER BY w.code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mapping_bp.route('/warehouses-accounts/<int:wid>', methods=['PUT'])
def update_warehouse_account(wid):
    d = request.get_json() or {}
    acc = d.get('account_code', '')
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب مطلوب'}), 400
    
    existing = db.query("SELECT code, name_ar FROM accounts WHERE code=?", (acc,), one=True)
    if not existing:
        return jsonify({'success': False, 'message': 'الحساب مش موجود'}), 400
    
    db.execute("UPDATE warehouses SET account_code=? WHERE id=?", (acc, wid))
    return jsonify({'success': True, 'message': 'تم التحديث'})


# ============================================================
# 6. البحث في الدليل (فلتر)
# ============================================================
@mapping_bp.route('/search-accounts', methods=['GET'])
def search_accounts():
    """بحث في الدليل بكود الحساب أو جزء من الاسم"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': True, 'data': []})
    
    rows = db.query("""
        SELECT code, name_ar, level, nature
        FROM accounts
        WHERE is_leaf = 1 AND is_active = 1
          AND (code LIKE ? OR name_ar LIKE ?)
        ORDER BY code
        LIMIT 50
    """, (f'%{q}%', f'%{q}%'))
    return jsonify({'success': True, 'data': json_safe(rows)})
