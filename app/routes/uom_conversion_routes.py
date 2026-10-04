from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

conv_bp = Blueprint('conversions', __name__)


@conv_bp.route('/item/<int:item_id>', methods=['GET'])
def list_conversions(item_id):
    """Get all conversions for an item (including base UOM)."""
    # Get item with base UOM
    item = db.query(
        """SELECT i.id, i.code, i.name_ar, i.base_uom_id, u.name_ar as base_uom_name, u.code as base_uom_code
           FROM items i
           JOIN units_of_measure u ON i.base_uom_id = u.id
           WHERE i.id=?""",
        (item_id,), one=True
    )
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    # Get other conversions
    convs = db.query(
        """SELECT uc.*, u.name_ar as uom_name, u.code as uom_code
           FROM uom_conversions uc
           JOIN units_of_measure u ON uc.to_uom_id = u.id
           WHERE uc.item_id=?
           ORDER BY uc.id""",
        (item_id,)
    )

    # Build full list: base + others
    all_units = [{
        'uom_id': item['base_uom_id'],
        'uom_name': item['base_uom_name'],
        'uom_code': item['base_uom_code'],
        'factor': 1.0,
        'is_base': True
    }]
    for c in convs:
        all_units.append({
            'id': c['id'],
            'uom_id': c['to_uom_id'],
            'uom_name': c['uom_name'],
            'uom_code': c['uom_code'],
            'factor': c['conversion_factor'],
            'is_base': False
        })

    return jsonify({
        'success': True,
        'data': {
            'item_id': item_id,
            'item_code': item['code'],
            'item_name': item['name_ar'],
            'base_uom_id': item['base_uom_id'],
            'units': all_units
        }
    })


@conv_bp.route('/item/<int:item_id>', methods=['POST'])
def add_conversion(item_id):
    """Add a conversion for an item (max 3 total including base)."""
    d = request.get_json() or {}
    if not d.get('to_uom_id') or not d.get('conversion_factor'):
        return jsonify({'success': False, 'message': 'to_uom_id و conversion_factor مطلوبان'}), 400

    # Check item exists
    item = db.query("SELECT base_uom_id FROM items WHERE id=?", (item_id,), one=True)
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    # Prevent same as base
    if int(d['to_uom_id']) == int(item['base_uom_id']):
        return jsonify({'success': False, 'message': 'لا يمكن إضافة الوحدة الأساسية كتحويل'}), 400

    # Check max 3 units total (base + 2 conversions)
    cnt = db.query("SELECT COUNT(*) as n FROM uom_conversions WHERE item_id=?", (item_id,), one=True)
    if cnt['n'] >= 2:
        return jsonify({'success': False, 'message': 'الحد الأقصى 3 وحدات للصنف (الأساسية + 2)'}), 400

    try:
        cid = db.execute(
            """INSERT INTO uom_conversions (item_id, from_uom_id, to_uom_id, conversion_factor)
               VALUES (?, ?, ?, ?)""",
            (item_id, item['base_uom_id'], d['to_uom_id'], d['conversion_factor'])
        )
        return jsonify({'success': True, 'data': {'id': cid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@conv_bp.route('/<int:conv_id>', methods=['DELETE'])
def delete_conversion(conv_id):
    db.execute("DELETE FROM uom_conversions WHERE id=?", (conv_id,))
    return jsonify({'success': True})


@conv_bp.route('/convert', methods=['POST'])
def convert_quantity():
    """Convert a quantity from one UOM to base UOM for a given item."""
    d = request.get_json() or {}
    item_id = d.get('item_id')
    uom_id = d.get('uom_id')
    qty = float(d.get('quantity', 0))

    item = db.query("SELECT base_uom_id FROM items WHERE id=?", (item_id,), one=True)
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    if int(uom_id) == int(item['base_uom_id']):
        factor = 1.0
    else:
        row = db.query(
            "SELECT conversion_factor FROM uom_conversions WHERE item_id=? AND to_uom_id=?",
            (item_id, uom_id), one=True
        )
        if not row:
            return jsonify({'success': False, 'message': 'لا يوجد تحويل لهذه الوحدة'}), 400
        factor = float(row['conversion_factor'])

    return jsonify({
        'success': True,
        'data': {
            'quantity': qty,
            'factor': factor,
            'base_quantity': qty * factor
        }
    })
