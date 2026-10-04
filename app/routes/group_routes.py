from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

group_bp = Blueprint('groups', __name__)


@group_bp.route('/', methods=['GET'])
def list_groups():
    """Return all groups as flat list with level info."""
    rows = db.query(
        """SELECT g.*, p.name_ar as parent_name,
                  u.name_ar as default_uom_name
           FROM item_groups g
           LEFT JOIN item_groups p ON g.parent_id = p.id
           LEFT JOIN units_of_measure u ON g.default_uom_id = u.id
           WHERE g.is_active=1
           ORDER BY g.level, g.code"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@group_bp.route('/tree', methods=['GET'])
def tree_groups():
    """Return groups in tree structure."""
    rows = db.query("SELECT * FROM item_groups WHERE is_active=1 ORDER BY code")
    rows = [dict(r) for r in rows]
    by_id = {r['id']: {**r, 'children': []} for r in rows}
    roots = []
    for r in rows:
        node = by_id[r['id']]
        if r['parent_id']:
            parent = by_id.get(r['parent_id'])
            if parent:
                parent['children'].append(node)
        else:
            roots.append(node)
    return jsonify({'success': True, 'data': json_safe(roots)})


@group_bp.route('/<int:gid>', methods=['GET'])
def get_group(gid):
    row = db.query("SELECT * FROM item_groups WHERE id=?", (gid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'المجموعة غير موجودة'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@group_bp.route('/', methods=['POST'])
def create_group():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        parent_id = d.get('parent_id')
        level = 1
        if parent_id:
            parent = db.query("SELECT level FROM item_groups WHERE id=?", (parent_id,), one=True)
            if parent:
                level = parent['level'] + 1
        gid = db.execute(
            """INSERT INTO item_groups 
               (code, name_ar, name_en, parent_id, level,
                inventory_account, cost_account, revenue_account, clearing_account,
                default_cost_method, default_uom_id, notes, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (d['code'], d['name_ar'], d.get('name_en'),
             parent_id, level,
             d.get('inventory_account'), d.get('cost_account'),
             d.get('revenue_account'), d.get('clearing_account'),
             d.get('default_cost_method', 'WEIGHTED_AVERAGE'),
             d.get('default_uom_id'), d.get('notes'))
        )
        return jsonify({'success': True, 'data': {'id': gid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@group_bp.route('/<int:gid>', methods=['PUT'])
def update_group(gid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'parent_id',
              'inventory_account', 'cost_account', 'revenue_account', 'clearing_account',
              'default_cost_method', 'default_uom_id', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(gid)
    db.execute(f"UPDATE item_groups SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@group_bp.route('/<int:gid>', methods=['DELETE'])
def delete_group(gid):
    # Check if has children or items
    children = db.query("SELECT COUNT(*) as n FROM item_groups WHERE parent_id=?", (gid,), one=True)
    items = db.query("SELECT COUNT(*) as n FROM items WHERE group_id=?", (gid,), one=True)
    if children['n'] > 0 or items['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف مجموعة بها فروع أو أصناف'}), 400
    db.execute("DELETE FROM item_groups WHERE id=?", (gid,))
    return jsonify({'success': True})
