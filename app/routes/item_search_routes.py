from flask import Blueprint, jsonify
from app.database import db
from app.utils import json_safe

search_bp = Blueprint('item_search', __name__)


@search_bp.route('/search-list', methods=['GET'])
def search_list():
    """قائمة الأصناف للبحث في كارت الصنف"""
    try:
        rows = db.query("""
            SELECT id, code, name_ar, name_en, item_type, base_uom_id
            FROM items
            WHERE is_active = 1
            ORDER BY code
        """)
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
