from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

tier_bp = Blueprint('tiers', __name__)


@tier_bp.route('/item/<int:item_id>', methods=['GET'])
def get_item_tiers(item_id):
    """Return all 3 tiers of an item with conversion factors."""
    item = db.query(
        """SELECT i.id, i.code, i.name_ar, i.base_uom_id,
                  i.medium_uom_id, i.medium_to_minor_factor,
                  i.major_uom_id, i.major_to_medium_factor
           FROM items i WHERE i.id=?""",
        (item_id,), one=True
    )
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    # Fetch UOM names
    uoms = {}
    for uid in [item['base_uom_id'], item['medium_uom_id'], item['major_uom_id']]:
        if uid:
            u = db.query("SELECT id, name_ar, code FROM units_of_measure WHERE id=?", (uid,), one=True)
            if u: uoms[uid] = u

    tiers = []

    # Major
    if item['major_uom_id'] and item['major_to_medium_factor']:
        u = uoms.get(item['major_uom_id'], {})
        tiers.append({
            'tier': 'MAJOR',
            'uom_id': item['major_uom_id'],
            'uom_name': u.get('name_ar',''),
            'uom_code': u.get('code',''),
            'to_next_factor': item['major_to_medium_factor'],
            'to_base_factor': None  # computed below
        })

    # Medium
    if item['medium_uom_id'] and item['medium_to_minor_factor']:
        u = uoms.get(item['medium_uom_id'], {})
        tiers.append({
            'tier': 'MEDIUM',
            'uom_id': item['medium_uom_id'],
            'uom_name': u.get('name_ar',''),
            'uom_code': u.get('code',''),
            'to_next_factor': item['medium_to_minor_factor'],
            'to_base_factor': item['medium_to_minor_factor']
        })

    # Minor = Base
    u = uoms.get(item['base_uom_id'], {})
    tiers.append({
        'tier': 'MINOR',
        'uom_id': item['base_uom_id'],
        'uom_name': u.get('name_ar',''),
        'uom_code': u.get('code',''),
        'to_next_factor': 1,
        'to_base_factor': 1
    })

    # Compute to_base for major
    if item['major_to_medium_factor'] and item['medium_to_minor_factor']:
        for t in tiers:
            if t['tier'] == 'MAJOR':
                t['to_base_factor'] = item['major_to_medium_factor'] * item['medium_to_minor_factor']

    return jsonify({
        'success': True,
        'data': {
            'item_id': item_id,
            'item_code': item['code'],
            'item_name': item['name_ar'],
            'base_uom_id': item['base_uom_id'],
            'tiers': tiers
        }
    })


@tier_bp.route('/item/<int:item_id>', methods=['PUT'])
def update_item_tiers(item_id):
    """Update the 3 tiers of an item."""
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT id FROM items WHERE id=?", (item_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

        # Validate base_uom_id (required)
        if not d.get('base_uom_id'):
            return jsonify({'success': False, 'message': 'الوحدة الصغرى (الأساسية) مطلوبة'}), 400

        base = int(d['base_uom_id'])
        medium = d.get('medium_uom_id')
        major = d.get('major_uom_id')
        mid_factor = d.get('medium_to_minor_factor')
        maj_factor = d.get('major_to_medium_factor')

        # Validations
        if medium and medium == base:
            return jsonify({'success': False, 'message': 'الوحدة المتوسطة يجب أن تختلف عن الصغرى'}), 400
        if major and (major == base or major == medium):
            return jsonify({'success': False, 'message': 'الوحدة الكبرى يجب أن تختلف عن الأخريين'}), 400
        if medium and not mid_factor:
            return jsonify({'success': False, 'message': 'أدخل معامل التحويل للوحدة المتوسطة'}), 400
        if major and not maj_factor:
            return jsonify({'success': False, 'message': 'أدخل معامل التحويل للوحدة الكبرى'}), 400
        if major and not medium:
            return jsonify({'success': False, 'message': 'لا يمكن إضافة وحدة كبرى بدون متوسطة'}), 400

        conn.execute(
            """UPDATE items SET
                 base_uom_id=?,
                 medium_uom_id=?, medium_to_minor_factor=?,
                 major_uom_id=?, major_to_medium_factor=?
               WHERE id=?""",
            (base,
             int(medium) if medium else None,
             float(mid_factor) if mid_factor else None,
             int(major) if major else None,
             float(maj_factor) if maj_factor else None,
             item_id)
        )

    return jsonify({'success': True, 'message': 'تم تحديث الوحدات'})


@tier_bp.route('/convert', methods=['POST'])
def convert_quantity():
    """Convert a quantity from any tier to the minor (base) unit."""
    d = request.get_json() or {}
    item_id = d.get('item_id')
    uom_id = d.get('uom_id')
    qty = float(d.get('quantity', 0))

    item = db.query(
        """SELECT base_uom_id, medium_uom_id, medium_to_minor_factor,
                  major_uom_id, major_to_medium_factor
           FROM items WHERE id=?""",
        (item_id,), one=True
    )
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    uom_id = int(uom_id)
    factor = None

    if uom_id == item['base_uom_id']:
        factor = 1.0
    elif item['medium_uom_id'] and uom_id == item['medium_uom_id']:
        factor = float(item['medium_to_minor_factor'] or 1)
    elif item['major_uom_id'] and uom_id == item['major_uom_id']:
        factor = float(item['major_to_medium_factor'] or 1) * float(item['medium_to_minor_factor'] or 1)

    if factor is None:
        return jsonify({'success': False, 'message': 'هذه الوحدة ليست من وحدات الصنف'}), 400

    return jsonify({
        'success': True,
        'data': {
            'quantity': qty,
            'uom_id': uom_id,
            'base_quantity': qty * factor,
            'factor': factor
        }
    })
