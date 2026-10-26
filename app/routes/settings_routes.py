from flask import Blueprint, request, jsonify
from app.database import db
from app.services.settings_service import clear_cache

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/<category>', methods=['GET'])
def get_settings(category):
    """جلب كل إعدادات فئة معينة"""
    rows = db.query(
        "SELECT key, value, value_type, label_ar FROM settings WHERE category=? ORDER BY id",
        (category,)
    )
    result = {}
    for r in rows:
        val = r['value']
        vtype = r['value_type'] or 'string'
        if vtype == 'bool':
            val = val in ('1', 'true', 'True')
        elif vtype == 'int':
            try: val = int(val)
            except: val = 0
        elif vtype == 'float':
            try: val = float(val)
            except: val = 0.0
        result[r['key']] = val
    return jsonify({'success': True, 'data': result})


@settings_bp.route('/<category>', methods=['PUT', 'POST'])
def update_settings(category):
    """تحديث إعدادات فئة معينة (bulk)"""
    d = request.get_json() or {}
    if not d:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400

    with db.transaction() as conn:
        for key, value in d.items():
            # تحويل bool → '1'/'0'
            if isinstance(value, bool):
                val_str = '1' if value else '0'
                vtype = 'bool'
            elif isinstance(value, int):
                val_str = str(value)
                vtype = 'int'
            elif isinstance(value, float):
                val_str = str(value)
                vtype = 'float'
            else:
                val_str = str(value) if value is not None else ''
                vtype = 'string'

            # upsert
            conn.execute("""
                INSERT INTO settings (category, key, value, value_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    value_type = excluded.value_type,
                    updated_at = CURRENT_TIMESTAMP
            """, (category, key, val_str, vtype))

    # ✅ مسح الـ cache عشان التغييرات تظهر فورًا
    clear_cache(category)

    return jsonify({'success': True, 'message': 'تم الحفظ'})


@settings_bp.route('/<category>/<key>', methods=['GET'])
def get_setting(category, key):
    """جلب إعداد واحد"""
    row = db.query(
        "SELECT value, value_type FROM settings WHERE category=? AND key=?",
        (category, key), one=True
    )
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404

    val = row['value']
    if row['value_type'] == 'bool':
        val = val in ('1', 'true', 'True')

    return jsonify({'success': True, 'data': {'key': key, 'value': val}})


@settings_bp.route('/all', methods=['GET'])
def get_all_settings():
    """جلب كل الإعدادات (كل الفئات)"""
    rows = db.query("SELECT category, key, value, value_type FROM settings ORDER BY category, id")
    result = {}
    for r in rows:
        if r['category'] not in result:
            result[r['category']] = {}
        val = r['value']
        vtype = r['value_type'] or 'string'
        if vtype == 'bool':
            val = val in ('1', 'true', 'True')
        elif vtype == 'int':
            try: val = int(val)
            except: val = 0
        elif vtype == 'float':
            try: val = float(val)
            except: val = 0.0
        result[r['category']][r['key']] = val
    return jsonify({'success': True, 'data': result})
