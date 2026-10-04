from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

account_bp = Blueprint('accounts', __name__)


@account_bp.route('/', methods=['GET'])
def list_accounts():
    cond, vals = ['1=1'], []
    if request.args.get('level'):
        cond.append('level = ?'); vals.append(request.args.get('level'))
    if request.args.get('nature'):
        cond.append('nature = ?'); vals.append(request.args.get('nature'))
    if request.args.get('financial_statement'):
        cond.append('financial_statement = ?'); vals.append(request.args.get('financial_statement'))
    if request.args.get('search'):
        cond.append('(code LIKE ? OR name_ar LIKE ? OR name_en LIKE ?)')
        s = f"%{request.args.get('search')}%"
        vals.extend([s, s, s])
    if request.args.get('is_active') is not None:
        cond.append('is_active = ?'); vals.append(int(request.args.get('is_active')))
    where = ' AND '.join(cond)
    rows = db.query(f"SELECT * FROM accounts WHERE {where} ORDER BY code", vals)
    return jsonify({'success': True, 'data': json_safe(rows)})


@account_bp.route('/leaf', methods=['GET'])
def list_leaf():
    rows = db.query("SELECT * FROM accounts WHERE is_leaf=1 AND is_active=1 ORDER BY code")
    return jsonify({'success': True, 'data': json_safe(rows)})


@account_bp.route('/tree', methods=['GET'])
def tree_accounts():
    rows = db.query("SELECT * FROM accounts WHERE is_active=1 ORDER BY code")
    rows = [dict(r) for r in rows]
    by_code = {r['code']: {**r, 'children': []} for r in rows}
    roots = []
    for r in rows:
        if r['parent_code'] and r['parent_code'] in by_code:
            by_code[r['parent_code']]['children'].append(by_code[r['code']])
        else:
            roots.append(by_code[r['code']])
    return jsonify({'success': True, 'data': json_safe(roots)})


@account_bp.route('/<int:aid>', methods=['GET'])
def get_account(aid):
    row = db.query("SELECT * FROM accounts WHERE id=?", (aid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@account_bp.route('/by-code/<path:code>', methods=['GET'])
def get_by_code(code):
    row = db.query("SELECT * FROM accounts WHERE code=?", (code,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@account_bp.route('/', methods=['POST'])
def create_account():
    d = request.get_json() or {}
    for f in ['code', 'name_ar', 'level', 'nature']:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'الحقل {f} مطلوب'}), 400
    try:
        aid = db.execute("""
            INSERT INTO accounts
            (code, name_ar, name_en, level, parent_code, nature, financial_statement,
             bs_group, pl_group, is_group, is_leaf, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d['code'], d['name_ar'], d.get('name_en'),
            d['level'], d.get('parent_code'),
            d['nature'], d.get('financial_statement'),
            d.get('bs_group'), d.get('pl_group'),
            d.get('is_group', 0), d.get('is_leaf', 1), d.get('is_active', 1)
        ))
        # Update parent is_group
        if d.get('parent_code'):
            db.execute("UPDATE accounts SET is_group=1, is_leaf=0 WHERE code=?", (d['parent_code'],))
        return jsonify({'success': True, 'data': {'id': aid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@account_bp.route('/<int:aid>', methods=['PUT'])
def update_account(aid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'level', 'parent_code', 'nature',
              'financial_statement', 'bs_group', 'pl_group', 'is_active', 'is_group', 'is_leaf']:
        if k in d:
            fields.append(f"{k}=?"); values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(aid)
    db.execute(f"UPDATE accounts SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@account_bp.route('/<int:aid>', methods=['DELETE'])
def delete_account(aid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT code FROM accounts WHERE id=?", (aid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        code = row['code']
        cur = conn.execute("SELECT COUNT(*) as n FROM accounts WHERE parent_code=?", (code,))
        if cur.fetchone()['n'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف حساب له فروع'}), 400
        cur = conn.execute("SELECT COUNT(*) as n FROM journal_entry_lines WHERE account_code=?", (code,))
        if cur.fetchone()['n'] > 0:
            return jsonify({'success': False, 'message': 'الحساب مستخدم في قيود'}), 400
        conn.execute("DELETE FROM accounts WHERE id=?", (aid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@account_bp.route('/types', methods=['GET'])
def list_types():
    rows = db.query("SELECT * FROM account_types ORDER BY code")
    return jsonify({'success': True, 'data': json_safe(rows)})
