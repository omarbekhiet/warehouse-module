"""
إضافة TAX & DISCOUNT APIs + PAYMENT LINES APIs
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'cash_box_routes.py')

print("=" * 60)
print("🔧 إضافة APIs جديدة")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# نظّف الملف
content = content.rstrip()

new_apis = '''


# =========================================
# TAX & DISCOUNT SETTINGS
# =========================================

@cb_bp.route('/tax-settings/', methods=['GET'])
def list_tax_settings():
    rows = db.query("SELECT * FROM tax_settings WHERE is_active=1 ORDER BY id")
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/tax-settings/', methods=['POST'])
def create_tax_setting():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar') or not d.get('account_code'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    tid = db.execute("""
        INSERT INTO tax_settings 
        (code, name_ar, name_en, tax_type, rate, account_code, 
         is_default, applies_to, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (d['code'], d['name_ar'], d.get('name_en'),
          d.get('tax_type', 'VAT'), float(d.get('rate', 0)),
          d['account_code'], d.get('is_default', 0),
          d.get('applies_to', 'BOTH'), d.get('notes')))
    return jsonify({'success': True, 'data': {'id': tid}}), 201


@cb_bp.route('/tax-settings/<int:tid>', methods=['PUT'])
def update_tax_setting(tid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'rate', 'account_code', 'is_active', 'applies_to', 'notes']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(tid)
    db.execute(f"UPDATE tax_settings SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True})


@cb_bp.route('/tax-settings/<int:tid>', methods=['DELETE'])
def delete_tax_setting(tid):
    db.execute("DELETE FROM tax_settings WHERE id=?", (tid,))
    return jsonify({'success': True})


@cb_bp.route('/discount-settings/', methods=['GET'])
def list_discount_settings():
    rows = db.query("SELECT * FROM discount_settings WHERE is_active=1 ORDER BY id")
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/discount-settings/', methods=['POST'])
def create_discount_setting():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar') or not d.get('account_code'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    did = db.execute("""
        INSERT INTO discount_settings 
        (code, name_ar, name_en, discount_type, default_rate, 
         account_code, applies_to, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (d['code'], d['name_ar'], d.get('name_en'),
          d.get('discount_type', 'TRADE'), float(d.get('default_rate', 0)),
          d['account_code'], d.get('applies_to', 'BOTH'), d.get('notes')))
    return jsonify({'success': True, 'data': {'id': did}}), 201


@cb_bp.route('/discount-settings/<int:did>', methods=['PUT'])
def update_discount_setting(did):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'default_rate', 'account_code', 'is_active', 'applies_to', 'notes']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(did)
    db.execute(f"UPDATE discount_settings SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True})


@cb_bp.route('/discount-settings/<int:did>', methods=['DELETE'])
def delete_discount_setting(did):
    db.execute("DELETE FROM discount_settings WHERE id=?", (did,))
    return jsonify({'success': True})


# =========================================
# PAYMENT LINES
# =========================================

@cb_bp.route('/payment-lines/<string:parent_type>/<int:parent_id>', methods=['GET'])
def get_payment_lines(parent_type, parent_id):
    rows = db.query("""
        SELECT * FROM payment_lines 
        WHERE parent_type=? AND parent_id=?
        ORDER BY line_no
    """, (parent_type, parent_id))
    return jsonify({'success': True, 'data': json_safe(rows)})
'''

# ضيف الكود الجديد
content += new_apis

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
print(f"✅ تم إضافة APIs جديدة")
print(f"  حجم الملف: {len(content)} bytes")