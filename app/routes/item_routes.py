from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

item_bp = Blueprint('items', __name__)


@item_bp.route('/', methods=['GET'])
def list_items():
    search = request.args.get('search', '')
    conditions, values = ["1=1"], []
    if search:
        conditions.append("(i.code LIKE ? OR i.name_ar LIKE ?)")
        values += [f'%{search}%', f'%{search}%']
    where = ' AND '.join(conditions)
    rows = db.query(
        f"""SELECT i.*, 
                   u.name_ar as base_uom_name,
                   m.name_ar as medium_uom_name,
                   j.name_ar as major_uom_name,
                   g.code as group_code,
                   g.name_ar as group_name,
                   g.inventory_account as group_inventory_account,
                   g.cost_account as group_cost_account,
                   g.revenue_account as group_revenue_account,
                   g.clearing_account as group_clearing_account
            FROM items i
            LEFT JOIN units_of_measure u ON i.base_uom_id = u.id
            LEFT JOIN units_of_measure m ON i.medium_uom_id = m.id
            LEFT JOIN units_of_measure j ON i.major_uom_id = j.id
            LEFT JOIN item_groups g ON i.group_id = g.id
            WHERE {where}
            ORDER BY i.code""",
        values
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@item_bp.route('/<int:iid>', methods=['GET'])
def get_item(iid):
    row = db.query(
        """SELECT i.*,
                  u.name_ar as base_uom_name, u.code as base_uom_code,
                  m.name_ar as medium_uom_name, m.code as medium_uom_code,
                  j.name_ar as major_uom_name, j.code as major_uom_code,
                  g.code as group_code, g.name_ar as group_name,
                  g.inventory_account as group_inventory_account,
                  g.cost_account as group_cost_account,
                  g.revenue_account as group_revenue_account,
                  g.clearing_account as group_clearing_account,
                  g.default_cost_method as group_cost_method
           FROM items i
           LEFT JOIN units_of_measure u ON i.base_uom_id = u.id
           LEFT JOIN units_of_measure m ON i.medium_uom_id = m.id
           LEFT JOIN units_of_measure j ON i.major_uom_id = j.id
           LEFT JOIN item_groups g ON i.group_id = g.id
           WHERE i.id=?""",
        (iid,), one=True
    )
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@item_bp.route('/', methods=['POST'])
def create_item():
    d = request.get_json() or {}
    required = ['code', 'name_ar', 'item_type', 'base_uom_id',
                'inventory_account', 'cost_account']
    for f in required:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'الحقل {f} مطلوب'}), 400

    try:
        iid = db.execute(
            """INSERT INTO items (code, name_ar, name_en, category_id, group_id, item_type,
               base_uom_id, cost_method, inventory_account, cost_account,
               revenue_account, clearing_account, reorder_level, is_active,
               medium_uom_id, medium_to_minor_factor,
               major_uom_id, major_to_medium_factor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
            (d['code'], d['name_ar'], d.get('name_en'),
             d.get('category_id', 1),
             d.get('group_id'),
             d['item_type'], d['base_uom_id'],
             d.get('cost_method', 'WEIGHTED_AVERAGE'),
             d['inventory_account'], d['cost_account'],
             d.get('revenue_account'),
             d.get('clearing_account'),
             d.get('reorder_level', 0),
             d.get('medium_uom_id'), d.get('medium_to_minor_factor'),
             d.get('major_uom_id'), d.get('major_to_medium_factor'))
        )
        return jsonify({'success': True, 'data': {'id': iid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@item_bp.route('/<int:iid>', methods=['PUT'])
def update_item(iid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'category_id', 'group_id', 'item_type',
              'base_uom_id', 'cost_method', 'inventory_account', 'cost_account',
              'revenue_account', 'clearing_account', 'reorder_level',
              'medium_uom_id', 'medium_to_minor_factor',
              'major_uom_id', 'major_to_medium_factor', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(iid)
    db.execute(f"UPDATE items SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@item_bp.route('/<int:iid>/stock', methods=['GET'])
def item_stock(iid):
    rows = db.query(
        """SELECT sb.*, w.name_ar as warehouse_name
           FROM stock_balances sb
           JOIN warehouses w ON sb.warehouse_id = w.id
           WHERE sb.item_id=? AND sb.quantity != 0""",
        (iid,)
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@item_bp.route('/<int:iid>', methods=['DELETE'])
def delete_item(iid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE item_id=?", (iid,))
        if cur.fetchone()['q'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف صنف له رصيد'}), 400
        conn.execute("DELETE FROM uom_conversions WHERE item_id=?", (iid,))
        conn.execute("DELETE FROM items WHERE id=?", (iid,))
    return jsonify({'success': True, 'message': 'تم حذف الصنف'})
