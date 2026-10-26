"""
مسارات الخزائن والبنوك والبطاقات
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from datetime import datetime

cb_bp = Blueprint('cash_boxes', __name__)


# =========================================
# Helpers
# =========================================

def _next_code(prefix, table):
    """توليد كود تلقائي"""
    rows = db.query(f"SELECT code FROM {table} WHERE code LIKE ? ORDER BY id DESC LIMIT 1", (f"{prefix}-%",))
    if not rows:
        return f"{prefix}-01"
    last = rows[0]['code']
    try:
        n = int(last.split('-')[-1]) + 1
    except:
        n = 1
    return f"{prefix}-{n:02d}"


# =========================================
# CASH BOXES
# =========================================

@cb_bp.route('/boxes/', methods=['GET'])
def list_boxes():
    """قائمة الخزائن"""
    rows = db.query("""
        SELECT cb.*, 
               p.name_ar as parent_name,
               a.name_ar as account_name
        FROM cash_boxes cb
        LEFT JOIN cash_boxes p ON cb.parent_id = p.id
        LEFT JOIN accounts a ON cb.account_code = a.code
        WHERE cb.is_active = 1
        ORDER BY cb.box_type DESC, cb.code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/boxes/<int:bid>', methods=['GET'])
def get_box(bid):
    """جلب خزينة واحدة"""
    row = db.query("""
        SELECT cb.*, 
               p.name_ar as parent_name,
               a.name_ar as account_name
        FROM cash_boxes cb
        LEFT JOIN cash_boxes p ON cb.parent_id = p.id
        LEFT JOIN accounts a ON cb.account_code = a.code
        WHERE cb.id = ?
    """, (bid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cb_bp.route('/boxes/', methods=['POST'])
def create_box():
    """إنشاء خزينة جديدة"""
    d = request.get_json() or {}
    
    if not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الاسم مطلوب'}), 400
    if not d.get('account_code'):
        return jsonify({'success': False, 'message': 'الحساب مطلوب'}), 400
    
    # التحقق من الحساب
    acc = db.query("SELECT code FROM accounts WHERE code = ?", (d['account_code'],), one=True)
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 400
    
    # توليد الكود
    code = d.get('code') or _next_code('CASH', 'cash_boxes')
    
    # التحقق من عدم التكرار
    exists = db.query("SELECT id FROM cash_boxes WHERE code = ?", (code,), one=True)
    if exists:
        return jsonify({'success': False, 'message': 'الكود مستخدم'}), 400
    
    box_type = d.get('box_type', 'MAIN')
    parent_id = d.get('parent_id')
    
    # الفرعية لازم يكون لها أب
    if box_type == 'SUB' and not parent_id:
        return jsonify({'success': False, 'message': 'الخزينة الفرعية تحتاج خزينة أب'}), 400
    
    opening = float(d.get('opening_balance', 0) or 0)
    
    bid = db.execute("""
        INSERT INTO cash_boxes 
        (code, name_ar, name_en, parent_id, box_type, account_code,
         opening_balance, opening_date, current_balance,
         currency, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code, d['name_ar'], d.get('name_en'),
        parent_id, box_type, d['account_code'],
        opening, d.get('opening_date'),
        opening,  # current = opening في البداية
        d.get('currency', 'EGP'), d.get('notes'),
        1  # user_id
    ))
    
    return jsonify({'success': True, 'data': {'id': bid, 'code': code}}), 201


@cb_bp.route('/boxes/<int:bid>', methods=['PUT'])
def update_box(bid):
    """تعديل خزينة"""
    d = request.get_json() or {}
    
    box = db.query("SELECT * FROM cash_boxes WHERE id = ?", (bid,), one=True)
    if not box:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    fields = []
    values = []
    
    for k in ['name_ar', 'name_en', 'parent_id', 'box_type', 
              'account_code', 'currency', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    
    # الرصيد الافتتاحي
    if 'opening_balance' in d:
        opening = float(d['opening_balance'] or 0)
        diff = opening - float(box['opening_balance'] or 0)
        new_current = float(box['current_balance'] or 0) + diff
        fields.append("opening_balance = ?")
        values.append(opening)
        fields.append("current_balance = ?")
        values.append(new_current)
    
    if 'opening_date' in d:
        fields.append("opening_date = ?")
        values.append(d['opening_date'])
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(bid)
    db.execute(f"UPDATE cash_boxes SET {', '.join(fields)} WHERE id = ?", values)
    
    return jsonify({'success': True, 'message': 'تم التحديث'})


@cb_bp.route('/boxes/<int:bid>', methods=['DELETE'])
def delete_box(bid):
    """حذف خزينة"""
    # التحقق من عدم وجود خزائن فرعية
    children = db.query("SELECT COUNT(*) as n FROM cash_boxes WHERE parent_id = ?", (bid,), one=True)
    if children and children['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف خزينة لها فروع'}), 400
    
    # التحقق من عدم وجود حركات
    txns = db.query(
        "SELECT COUNT(*) as n FROM cash_box_transactions WHERE box_id = ? AND box_type = 'CASH_BOX'",
        (bid,), one=True
    )
    if txns and txns['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف خزينة لها حركات'}), 400
    
    db.execute("DELETE FROM cash_boxes WHERE id = ?", (bid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# BANKS
# =========================================

@cb_bp.route('/banks/', methods=['GET'])
def list_banks():
    rows = db.query("""
        SELECT b.*, a.name_ar as account_name
        FROM banks b
        LEFT JOIN accounts a ON b.account_code = a.code
        WHERE b.is_active = 1
        ORDER BY b.code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/banks/<int:bid>', methods=['GET'])
def get_bank(bid):
    row = db.query("""
        SELECT b.*, a.name_ar as account_name
        FROM banks b
        LEFT JOIN accounts a ON b.account_code = a.code
        WHERE b.id = ?
    """, (bid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cb_bp.route('/banks/', methods=['POST'])
def create_bank():
    d = request.get_json() or {}
    
    if not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الاسم مطلوب'}), 400
    
    account_code = d.get('account_code', '1212')
    acc = db.query("SELECT code FROM accounts WHERE code = ?", (account_code,), one=True)
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 400
    
    code = d.get('code') or _next_code('BANK', 'banks')
    exists = db.query("SELECT id FROM banks WHERE code = ?", (code,), one=True)
    if exists:
        return jsonify({'success': False, 'message': 'الكود مستخدم'}), 400
    
    opening = float(d.get('opening_balance', 0) or 0)
    
    bid = db.execute("""
        INSERT INTO banks 
        (code, name_ar, name_en, account_code, account_number, iban,
         swift_code, branch_name, branch_address, contact_person, phone,
         opening_balance, opening_date, current_balance,
         currency, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code, d['name_ar'], d.get('name_en'), account_code,
        d.get('account_number'), d.get('iban'), d.get('swift_code'),
        d.get('branch_name'), d.get('branch_address'),
        d.get('contact_person'), d.get('phone'),
        opening, d.get('opening_date'), opening,
        d.get('currency', 'EGP'), d.get('notes'), 1
    ))
    
    return jsonify({'success': True, 'data': {'id': bid, 'code': code}}), 201


@cb_bp.route('/banks/<int:bid>', methods=['PUT'])
def update_bank(bid):
    d = request.get_json() or {}
    
    bank = db.query("SELECT * FROM banks WHERE id = ?", (bid,), one=True)
    if not bank:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    fields = []
    values = []
    
    for k in ['name_ar', 'name_en', 'account_code', 'account_number', 'iban',
              'swift_code', 'branch_name', 'branch_address', 'contact_person',
              'phone', 'currency', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    
    if 'opening_balance' in d:
        opening = float(d['opening_balance'] or 0)
        diff = opening - float(bank['opening_balance'] or 0)
        new_current = float(bank['current_balance'] or 0) + diff
        fields.append("opening_balance = ?")
        values.append(opening)
        fields.append("current_balance = ?")
        values.append(new_current)
    
    if 'opening_date' in d:
        fields.append("opening_date = ?")
        values.append(d['opening_date'])
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(bid)
    db.execute(f"UPDATE banks SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@cb_bp.route('/banks/<int:bid>', methods=['DELETE'])
def delete_bank(bid):
    # التحقق من البطاقات المرتبطة
    cards = db.query("SELECT COUNT(*) as n FROM payment_cards WHERE bank_id = ?", (bid,), one=True)
    if cards and cards['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف بنك له بطاقات مرتبطة'}), 400
    
    txns = db.query(
        "SELECT COUNT(*) as n FROM cash_box_transactions WHERE box_id = ? AND box_type = 'BANK'",
        (bid,), one=True
    )
    if txns and txns['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف بنك له حركات'}), 400
    
    db.execute("DELETE FROM banks WHERE id = ?", (bid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# CARDS
# =========================================

@cb_bp.route('/cards/', methods=['GET'])
def list_cards():
    rows = db.query("""
        SELECT c.*, 
               b.name_ar as bank_name,
               a.name_ar as account_name
        FROM payment_cards c
        LEFT JOIN banks b ON c.bank_id = b.id
        LEFT JOIN accounts a ON c.account_code = a.code
        WHERE c.is_active = 1
        ORDER BY c.code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/cards/<int:cid>', methods=['GET'])
def get_card(cid):
    row = db.query("""
        SELECT c.*, b.name_ar as bank_name, a.name_ar as account_name
        FROM payment_cards c
        LEFT JOIN banks b ON c.bank_id = b.id
        LEFT JOIN accounts a ON c.account_code = a.code
        WHERE c.id = ?
    """, (cid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cb_bp.route('/cards/', methods=['POST'])
def create_card():
    d = request.get_json() or {}
    
    if not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الاسم مطلوب'}), 400
    
    account_code = d.get('account_code', '1213')
    acc = db.query("SELECT code FROM accounts WHERE code = ?", (account_code,), one=True)
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 400
    
    code = d.get('code') or _next_code('CARD', 'payment_cards')
    exists = db.query("SELECT id FROM payment_cards WHERE code = ?", (code,), one=True)
    if exists:
        return jsonify({'success': False, 'message': 'الكود مستخدم'}), 400
    
    opening = float(d.get('opening_balance', 0) or 0)
    
    cid = db.execute("""
        INSERT INTO payment_cards
        (code, name_ar, name_en, card_type, bank_id, account_code,
         card_last4, card_holder, expiry_date, credit_limit,
         opening_balance, current_balance, currency, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code, d['name_ar'], d.get('name_en'),
        d.get('card_type', 'DEBIT'), d.get('bank_id'), account_code,
        d.get('card_last4'), d.get('card_holder'), d.get('expiry_date'),
        float(d.get('credit_limit', 0) or 0),
        opening, opening,
        d.get('currency', 'EGP'), d.get('notes'), 1
    ))
    
    return jsonify({'success': True, 'data': {'id': cid, 'code': code}}), 201


@cb_bp.route('/cards/<int:cid>', methods=['PUT'])
def update_card(cid):
    d = request.get_json() or {}
    
    card = db.query("SELECT * FROM payment_cards WHERE id = ?", (cid,), one=True)
    if not card:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    fields = []
    values = []
    
    for k in ['name_ar', 'name_en', 'card_type', 'bank_id', 'account_code',
              'card_last4', 'card_holder', 'expiry_date', 'credit_limit',
              'currency', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    
    if 'opening_balance' in d:
        opening = float(d['opening_balance'] or 0)
        diff = opening - float(card['opening_balance'] or 0)
        new_current = float(card['current_balance'] or 0) + diff
        fields.append("opening_balance = ?")
        values.append(opening)
        fields.append("current_balance = ?")
        values.append(new_current)
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(cid)
    db.execute(f"UPDATE payment_cards SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@cb_bp.route('/cards/<int:cid>', methods=['DELETE'])
def delete_card(cid):
    txns = db.query(
        "SELECT COUNT(*) as n FROM cash_box_transactions WHERE box_id = ? AND box_type = 'CARD'",
        (cid,), one=True
    )
    if txns and txns['n'] > 0:
        return jsonify({'success': False, 'message': 'لا يمكن حذف بطاقة لها حركات'}), 400
    
    db.execute("DELETE FROM payment_cards WHERE id = ?", (cid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# Stats + Lookups
# =========================================

@cb_bp.route('/stats', methods=['GET'])
def get_stats():
    """إحصائيات عامة"""
    boxes = db.query("SELECT COUNT(*) as n, COALESCE(SUM(current_balance),0) as total FROM cash_boxes WHERE is_active=1", one=True)
    banks = db.query("SELECT COUNT(*) as n, COALESCE(SUM(current_balance),0) as total FROM banks WHERE is_active=1", one=True)
    cards = db.query("SELECT COUNT(*) as n, COALESCE(SUM(current_balance),0) as total FROM payment_cards WHERE is_active=1", one=True)
    
    return jsonify({
        'success': True,
        'data': {
            'boxes': {'count': boxes['n'], 'total': float(boxes['total'])},
            'banks': {'count': banks['n'], 'total': float(banks['total'])},
            'cards': {'count': cards['n'], 'total': float(cards['total'])},
            'grand_total': float(boxes['total']) + float(banks['total']) + float(cards['total'])
        }
    })


@cb_bp.route('/accounts/leaves', methods=['GET'])
def accounts_leaves():
    """الحسابات القابلة للترحيل (leaf) لاختيار حساب الربط"""
    rows = db.query("""
        SELECT code, name_ar, name_en, parent_code, level
        FROM accounts
        WHERE is_leaf = 1 AND is_active = 1
        ORDER BY code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})



# =========================================
# Transactions (الحركات)
# =========================================

from app.services.cash_box_service import cash_box_service


@cb_bp.route('/transactions/', methods=['GET'])
def list_transactions():
    """قائمة الحركات"""
    box_type = request.args.get('box_type')
    box_id = request.args.get('box_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    limit = request.args.get('limit', 200, type=int)
    
    rows = cash_box_service.list_transactions(
        box_type=box_type, box_id=box_id,
        date_from=date_from, date_to=date_to, limit=limit
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/transactions/', methods=['POST'])
def create_transaction():
    """إنشاء حركة (إيداع/سحب)"""
    d = request.get_json() or {}
    result = cash_box_service.create_transaction(d, user_id=1)
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@cb_bp.route('/transactions/<int:tid>', methods=['GET'])
def get_transaction(tid):
    """جلب حركة واحدة"""
    row = db.query("""
        SELECT t.*,
               CASE t.box_type 
                   WHEN 'CASH_BOX' THEN cb.name_ar
                   WHEN 'BANK' THEN b.name_ar
                   WHEN 'CARD' THEN c.name_ar
               END as box_name
        FROM cash_box_transactions t
        LEFT JOIN cash_boxes cb ON t.box_type='CASH_BOX' AND t.box_id = cb.id
        LEFT JOIN banks b ON t.box_type='BANK' AND t.box_id = b.id
        LEFT JOIN payment_cards c ON t.box_type='CARD' AND t.box_id = c.id
        WHERE t.id = ?
    """, (tid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cb_bp.route('/transfers/', methods=['POST'])
def transfer_between_boxes():
    """تحويل بين خزنتين"""
    d = request.get_json() or {}
    result = cash_box_service.transfer_between_boxes(d, user_id=1)
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@cb_bp.route('/transactions/summary', methods=['GET'])
def transactions_summary():
    """ملخص الحركات حسب النوع"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    sql = """
        SELECT 
            txn_type,
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total
        FROM cash_box_transactions
        WHERE 1=1
    """
    params = []
    
    if date_from:
        sql += " AND txn_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND txn_date <= ?"
        params.append(date_to)
    
    sql += " GROUP BY txn_type"
    
    rows = db.query(sql, params)
    
    result = {
        'DEPOSIT': {'count': 0, 'total': 0},
        'WITHDRAW': {'count': 0, 'total': 0},
        'TRANSFER_IN': {'count': 0, 'total': 0},
        'TRANSFER_OUT': {'count': 0, 'total': 0}
    }
    
    for r in rows:
        result[r['txn_type']] = {
            'count': r['count'],
            'total': float(r['total'])
        }
    
    return jsonify({'success': True, 'data': result})


@cb_bp.route('/all-active/', methods=['GET'])
def list_all_active():
    """كل الخزائن والبنوك والبطاقات النشطة (للاختيار في التحويل)"""
    boxes = db.query("SELECT id, code, name_ar, current_balance FROM cash_boxes WHERE is_active=1")
    banks = db.query("SELECT id, code, name_ar, current_balance FROM banks WHERE is_active=1")
    cards = db.query("SELECT id, code, name_ar, current_balance FROM payment_cards WHERE is_active=1")
    
    result = []
    for b in boxes:
        result.append({'id': b['id'], 'box_type': 'CASH_BOX', 'code': b['code'], 
                      'name': b['name_ar'], 'balance': float(b['current_balance'] or 0)})
    for b in banks:
        result.append({'id': b['id'], 'box_type': 'BANK', 'code': b['code'], 
                      'name': b['name_ar'], 'balance': float(b['current_balance'] or 0)})
    for c in cards:
        result.append({'id': c['id'], 'box_type': 'CARD', 'code': c['code'], 
                      'name': c['name_ar'], 'balance': float(c['current_balance'] or 0)})
    
    



# =========================================
# BANK RECONCILIATION (التسوية البنكية)
# =========================================

@cb_bp.route('/reconciliations/', methods=['GET'])
def list_reconciliations():
    """قائمة التسويات"""
    bank_id = request.args.get('bank_id', type=int)
    status = request.args.get('status')
    
    sql = """
        SELECT r.*, 
               b.name_ar as bank_name,
               b.account_code,
               u.full_name as created_by_name
        FROM bank_reconciliations r
        LEFT JOIN banks b ON r.bank_id = b.id
        LEFT JOIN users u ON r.created_by = u.id
        WHERE 1=1
    """
    params = []
    if bank_id:
        sql += " AND r.bank_id = ?"
        params.append(bank_id)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.reconciliation_date DESC, r.id DESC LIMIT 100"
    
    rows = db.query(sql, params)
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/reconciliations/<int:rid>', methods=['GET'])
def get_reconciliation(rid):
    """جلب تسوية"""
    row = db.query("""
        SELECT r.*, b.name_ar as bank_name, b.account_code
        FROM bank_reconciliations r
        LEFT JOIN banks b ON r.bank_id = b.id
        WHERE r.id = ?
    """, (rid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    items = db.query("""
        SELECT * FROM bank_reconciliation_items 
        WHERE reconciliation_id = ?
        ORDER BY txn_date
    """, (rid,))
    
    result = dict(row)
    result['items'] = [dict(i) for i in items]
    return jsonify({'success': True, 'data': json_safe(result)})


@cb_bp.route('/reconciliations/', methods=['POST'])
def create_reconciliation():
    """إنشاء تسوية جديدة"""
    d = request.get_json() or {}
    
    bank_id = d.get('bank_id')
    recon_date = d.get('reconciliation_date')
    statement_balance = float(d.get('statement_balance', 0))
    
    if not bank_id or not recon_date:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    # جلب رصيد البنك من النظام
    bank = db.query("SELECT current_balance FROM banks WHERE id=?", (bank_id,), one=True)
    if not bank:
        return jsonify({'success': False, 'message': 'البنك غير موجود'}), 404
    
    system_balance = float(bank['current_balance'] or 0)
    difference = statement_balance - system_balance
    
    rid = db.execute("""
        INSERT INTO bank_reconciliations 
        (bank_id, reconciliation_date, statement_balance, system_balance, 
         difference, status, notes, created_by)
        VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, 1)
    """, (bank_id, recon_date, statement_balance, system_balance, 
          difference, d.get('notes')))
    
    return jsonify({
        'success': True,
        'data': {
            'id': rid,
            'difference': difference
        }
    }), 201


@cb_bp.route('/reconciliations/<int:rid>', methods=['PUT'])
def update_reconciliation(rid):
    """تحديث تسوية"""
    d = request.get_json() or {}
    
    fields, values = [], []
    for k in ['status', 'notes', 'statement_balance']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(rid)
    db.execute(f"UPDATE bank_reconciliations SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True})


@cb_bp.route('/reconciliations/<int:rid>', methods=['DELETE'])
def delete_reconciliation(rid):
    """حذف تسوية"""
    db.execute("DELETE FROM bank_reconciliations WHERE id = ?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@cb_bp.route('/reconciliations/<int:rid>/auto-match', methods=['POST'])
def auto_match(rid):
    """مطابقة تلقائية للحركات"""
    recon = db.query("SELECT * FROM bank_reconciliations WHERE id=?", (rid,), one=True)
    if not recon:
        return jsonify({'success': False, 'message': 'التسوية غير موجودة'}), 404
    
    # جلب حركات البنك
    txns = db.query("""
        SELECT * FROM cash_box_transactions 
        WHERE box_type='BANK' AND box_id=?
          AND txn_date <= ?
        ORDER BY txn_date
    """, (recon['bank_id'], recon['reconciliation_date']))
    
    # امسح الحركات القديمة
    db.execute("DELETE FROM bank_reconciliation_items WHERE reconciliation_id=?", (rid,))
    
    # ضيف الحركات
    matched = 0
    for t in txns:
        db.execute("""
            INSERT INTO bank_reconciliation_items 
            (reconciliation_id, txn_type, reference_no, txn_date, amount, is_matched)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (rid, t['txn_type'], t['reference_no'], t['txn_date'], t['amount']))
        matched += 1
    
    return jsonify({
        'success': True,
        'data': {'matched': matched}
    })


# =========================================
# BRANCHES (الفروع)
# =========================================

@cb_bp.route('/branches/', methods=['GET'])
def list_branches():
    rows = db.query("SELECT * FROM branches WHERE is_active=1 ORDER BY code")
    return jsonify({'success': True, 'data': json_safe(rows)})


@cb_bp.route('/branches/<int:bid>', methods=['GET'])
def get_branch(bid):
    row = db.query("SELECT * FROM branches WHERE id=?", (bid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cb_bp.route('/branches/', methods=['POST'])
def create_branch():
    d = request.get_json() or {}
    
    if not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الاسم مطلوب'}), 400
    
    code = d.get('code')
    if not code:
        rows = db.query("SELECT code FROM branches WHERE code LIKE 'BR-%' ORDER BY id DESC LIMIT 1")
        if rows:
            try:
                n = int(rows[0]['code'].split('-')[-1]) + 1
            except:
                n = 1
        else:
            n = 1
        code = f"BR-{n:02d}"
    
    bid = db.execute("""
        INSERT INTO branches 
        (code, name_ar, name_en, address, phone, manager_name, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (code, d['name_ar'], d.get('name_en'), d.get('address'),
          d.get('phone'), d.get('manager_name'), d.get('notes')))
    
    return jsonify({'success': True, 'data': {'id': bid, 'code': code}}), 201


@cb_bp.route('/branches/<int:bid>', methods=['PUT'])
def update_branch(bid):
    d = request.get_json() or {}
    
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'address', 'phone', 'manager_name', 'is_active', 'notes']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(bid)
    db.execute(f"UPDATE branches SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True})


@cb_bp.route('/branches/<int:bid>', methods=['DELETE'])
def delete_branch(bid):
    db.execute("DELETE FROM branches WHERE id=?", (bid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# REPORTS (التقارير)
# =========================================

@cb_bp.route('/reports/summary', methods=['GET'])
def report_summary():
    """ملخص شامل"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # أرصدة
    boxes = db.query("SELECT COUNT(*) as cnt, COALESCE(SUM(current_balance),0) as total FROM cash_boxes WHERE is_active=1", one=True)
    banks = db.query("SELECT COUNT(*) as cnt, COALESCE(SUM(current_balance),0) as total FROM banks WHERE is_active=1", one=True)
    cards = db.query("SELECT COUNT(*) as cnt, COALESCE(SUM(current_balance),0) as total FROM payment_cards WHERE is_active=1", one=True)
    
    # حركات الفترة
    sql_txn = "SELECT txn_type, COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM cash_box_transactions WHERE 1=1"
    params = []
    if date_from:
        sql_txn += " AND txn_date >= ?"
        params.append(date_from)
    if date_to:
        sql_txn += " AND txn_date <= ?"
        params.append(date_to)
    sql_txn += " GROUP BY txn_type"
    
    txns = db.query(sql_txn, params)
    
    # مصروفات الفترة
    sql_exp = "SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM petty_cash_expenses WHERE 1=1"
    params = []
    if date_from:
        sql_exp += " AND expense_date >= ?"
        params.append(date_from)
    if date_to:
        sql_exp += " AND expense_date <= ?"
        params.append(date_to)
    expenses = db.query(sql_exp, params, one=True)
    
    txn_dict = {}
    for t in txns:
        txn_dict[t['txn_type']] = {'count': t['cnt'], 'total': float(t['total'])}
    
    return jsonify({
        'success': True,
        'data': {
            'balances': {
                'boxes': {'count': boxes['cnt'], 'total': float(boxes['total'])},
                'banks': {'count': banks['cnt'], 'total': float(banks['total'])},
                'cards': {'count': cards['cnt'], 'total': float(cards['total'])},
                'grand_total': float(boxes['total']) + float(banks['total']) + float(cards['total'])
            },
            'transactions': txn_dict,
            'expenses': {
                'count': expenses['cnt'],
                'total': float(expenses['total'])
            }
        }
    })


@cb_bp.route('/reports/box-statement/<box_type>/<int:box_id>', methods=['GET'])
def box_statement(box_type, box_id):
    """كشف حساب لخزينة/بنك/بطاقة"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # جلب الخزينة
    table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
    table = table_map.get(box_type)
    if not table:
        return jsonify({'success': False, 'message': 'نوع غير صحيح'}), 400
    
    box = db.query(f"SELECT * FROM {table} WHERE id=?", (box_id,), one=True)
    if not box:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    # الحركات
    sql = """
        SELECT * FROM cash_box_transactions 
        WHERE box_type=? AND box_id=?
    """
    params = [box_type, box_id]
    if date_from:
        sql += " AND txn_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND txn_date <= ?"
        params.append(date_to)
    sql += " ORDER BY txn_date, id"
    
    txns = db.query(sql, params)
    
    # حساب الرصيد الافتتاحي
    opening_balance = float(box['opening_balance'] or 0)
    if date_from:
        # احسب الرصيد قبل date_from
        sql_before = """
            SELECT COALESCE(SUM(
                CASE WHEN txn_type IN ('DEPOSIT', 'TRANSFER_IN') THEN amount
                     ELSE -amount END
            ), 0) as net
            FROM cash_box_transactions
            WHERE box_type=? AND box_id=? AND txn_date < ?
        """
        before = db.query(sql_before, (box_type, box_id, date_from), one=True)
        opening_balance = float(box['opening_balance'] or 0) + float(before['net'] or 0)
    
    # بناء الكشف مع الرصيد التراكمي
    running = opening_balance
    rows = []
    for t in txns:
        amount = float(t['amount'])
        if t['txn_type'] in ('DEPOSIT', 'TRANSFER_IN'):
            running += amount
            debit = amount
            credit = 0
        else:
            running -= amount
            debit = 0
            credit = amount
        
        rows.append({
            'date': t['txn_date'],
            'reference': t['reference_no'],
            'type': t['txn_type'],
            'description': t['description'],
            'debit': debit,
            'credit': credit,
            'balance': running
        })
    
    return jsonify({
        'success': True,
        'data': {
            'box': {
                'id': box['id'],
                'code': box['code'],
                'name': box['name_ar'],
                'account_code': box['account_code'],
                'current_balance': float(box['current_balance'] or 0)
            },
            'opening_balance': opening_balance,
            'transactions': rows,
            'closing_balance': running
        }
    })


@cb_bp.route('/reports/by-branch', methods=['GET'])
def report_by_branch():
    """تقرير حسب الفرع"""
    # ملاحظة: الفروع مربوطة بالخزائن عن طريق جدول جديد
    # لو مش موجود، نرجع كل الخزائن بدون فرع
    branches = db.query("SELECT * FROM branches WHERE is_active=1")
    
    result = []
    for b in branches:
        boxes = db.query("SELECT COUNT(*) as cnt, COALESCE(SUM(current_balance),0) as total FROM cash_boxes WHERE is_active=1", one=True)
        result.append({
            'branch_id': b['id'],
            'branch_code': b['code'],
            'branch_name': b['name_ar'],
            'boxes_count': boxes['cnt'],
            'boxes_total': float(boxes['total'])
        })
    
        # إجمالي عام
    total_all = db.query("SELECT COALESCE(SUM(current_balance),0) as total FROM cash_boxes WHERE is_active=1", one=True)
    
    return jsonify({
        'success': True,
        'data': {
            'branches': result,
            'total': float(total_all['total'])
        }
    })


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


# =========================================
# LINKING: MOVEMENTS <-> JOURNAL ENTRIES
# =========================================

@cb_bp.route('/link/search-by-reference', methods=['GET'])
def search_by_reference():
    """البحث عن حركة برقمها — ويرجع القيد المرتبط"""
    ref_no = request.args.get('ref_no', '').strip()
    if not ref_no:
        return jsonify({'success': False, 'message': 'رقم الحركة مطلوب'}), 400
    
    results = []
    
    # 1. supplier_payments
    sp = db.query("""
        SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
               payment_date as date, amount, 'دفعة مورد' as description,
               journal_entry_id
        FROM supplier_payments
        WHERE payment_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in sp:
        results.append(dict(r))
    
    # 2. customer_receipts
    cr = db.query("""
        SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
               receipt_date as date, amount, 'تحصيل عميل' as description,
               journal_entry_id
        FROM customer_receipts
        WHERE receipt_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in cr:
        results.append(dict(r))
    
    # 3. cash_box_transactions
    cbt = db.query("""
        SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
               txn_date as date, amount, description,
               journal_entry_id
        FROM cash_box_transactions
        WHERE reference_no = ?
    """, (ref_no,))
    for r in cbt:
        results.append(dict(r))
    
    # 4. petty_cash_expenses
    pce = db.query("""
        SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
               expense_date as date, amount, description,
               journal_entry_id
        FROM petty_cash_expenses
        WHERE expense_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in pce:
        results.append(dict(r))
    
    # 5. purchase_invoices
    pi = db.query("""
        SELECT 'PURCHASE_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount, 
               'فاتورة شراء' as description,
               journal_entry_id
        FROM purchase_invoices
        WHERE invoice_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in pi:
        results.append(dict(r))
    
    # 6. sales_invoices
    si = db.query("""
        SELECT 'SALES_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount,
               'فاتورة بيع' as description,
               journal_entry_id
        FROM sales_invoices
        WHERE invoice_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in si:
        results.append(dict(r))
    
    # 7. inventory_counts (جديد)
    ic = db.query("""
        SELECT 'INVENTORY_COUNT' as source_type, id, count_no as ref_no,
               count_date as date, 0 as amount, 'جرد مخزني' as description,
               journal_entry_id
        FROM inventory_counts
        WHERE count_no = ?
    """, (ref_no,))
    for r in ic:
        results.append(dict(r))
    
    # 8. stock_transactions (جديد)
    st = db.query("""
        SELECT 'STOCK_TRANSACTION' as source_type, id, transaction_no as ref_no,
               transaction_date as date, total_value as amount, 
               notes as description,
               journal_entry_id
        FROM stock_transactions
        WHERE transaction_no = ? AND journal_entry_id IS NOT NULL
    """, (ref_no,))
    for r in st:
        results.append(dict(r))
    
    # جلب القيود المرتبطة
    for r in results:
        if r.get('journal_entry_id'):
            je = db.query("""
                SELECT id, entry_no, entry_date, description, 
                       total_debit, total_credit, status
                FROM journal_entries WHERE id = ?
            """, (r['journal_entry_id'],), one=True)
            r['journal'] = dict(je) if je else None
            
            if je:
                lines = db.query("""
                    SELECT line_no, account_code, description,
                           debit_amount, credit_amount
                    FROM journal_entry_lines
                    WHERE journal_entry_id = ?
                    ORDER BY line_no
                """, (je['id'],))
                r['journal']['lines'] = [dict(l) for l in lines]
        else:
            r['journal'] = None
    
    return jsonify({
        'success': True,
        'data': json_safe(results),
        'count': len(results)
    })


@cb_bp.route('/link/search-by-journal/<int:je_id>', methods=['GET'])
def search_by_journal(je_id):
    """البحث عن حركة برقم القيد"""
    je = db.query("""
        SELECT * FROM journal_entries WHERE id = ?
    """, (je_id,), one=True)
    
    if not je:
        return jsonify({'success': False, 'message': 'القيد غير موجود'}), 404
    
    # جلب السطور
    lines = db.query("""
        SELECT * FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_no
    """, (je_id,))
    
    # جلب الحركة المرتبطة
    source = None
    ref_type = je['reference_type']
    ref_id = je['reference_id']
    
    tables_map = {
        'SUPPLIER_PAYMENT': ('supplier_payments', 'payment_no', 'payment_date', 'amount'),
        'CUSTOMER_RECEIPT': ('customer_receipts', 'receipt_no', 'receipt_date', 'amount'),
        'PETTY_CASH_EXPENSE': ('petty_cash_expenses', 'expense_no', 'expense_date', 'amount'),
        'PURCHASE_INVOICE': ('purchase_invoices', 'invoice_no', 'invoice_date', 'total_amount'),
        'SALES_INVOICE': ('sales_invoices', 'invoice_no', 'invoice_date', 'total_amount'),
        'PURCHASE_RETURN': ('purchase_returns', 'return_no', 'return_date', 'total_amount'),
        'SALES_RETURN': ('sales_returns', 'return_no', 'return_date', 'total_amount'),
        'CASH_BOX_TXN': ('cash_box_transactions', 'reference_no', 'txn_date', 'amount'),
        'CASH_BOX_TRANSFER': ('cash_box_transactions', 'reference_no', 'txn_date', 'amount'),
    }
    
    if ref_type in tables_map and ref_id:
        table, ref_field, date_field, amount_field = tables_map[ref_type]
        row = db.query(f"""
            SELECT *, {ref_field} as ref_no, {date_field} as date, 
                   {amount_field} as amount
            FROM {table} WHERE id = ?
        """, (ref_id,), one=True)
        if row:
            source = dict(row)
            source['source_type'] = ref_type
    
    return jsonify({
        'success': True,
        'data': {
            'journal': {
                'id': je['id'],
                'entry_no': je['entry_no'],
                'entry_date': je['entry_date'],
                'reference_type': ref_type,
                'reference_id': ref_id,
                'reference_no': je['reference_no'],
                'description': je['description'],
                'total_debit': je['total_debit'],
                'total_credit': je['total_credit'],
                'status': je['status'],
                'lines': [dict(l) for l in lines]
            },
            'source': source
        }
    })


@cb_bp.route('/link/movements-with-journals', methods=['GET'])
def movements_with_journals():
    """كل الحركات مع القيود في فترة"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    source_type = request.args.get('source_type')
    limit = request.args.get('limit', 200, type=int)
    
    params_base = []
    where_parts = []
    if date_from:
        where_parts.append("date >= ?")
    if date_to:
        where_parts.append("date <= ?")
    
    date_clause = " AND " + " AND ".join(where_parts) if where_parts else ""
    
    # نجمع الحركات من كل الجداول
    queries = {
        'SUPPLIER_PAYMENT': f"""
            SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
                   payment_date as date, amount, 'دفعة مورد' as description,
                   journal_entry_id
            FROM supplier_payments
            WHERE 1=1 {date_clause}
        """,
        'CUSTOMER_RECEIPT': f"""
            SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
                   receipt_date as date, amount, 'تحصيل عميل' as description,
                   journal_entry_id
            FROM customer_receipts
            WHERE 1=1 {date_clause}
        """,
        'CASH_BOX_TXN': f"""
            SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
                   txn_date as date, amount, description,
                   journal_entry_id
            FROM cash_box_transactions
            WHERE 1=1 {date_clause}
        """,
        'PETTY_CASH_EXPENSE': f"""
            SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
                   expense_date as date, amount, description,
                   journal_entry_id
            FROM petty_cash_expenses
            WHERE 1=1 {date_clause}
        """,
        'INVENTORY_COUNT': f"""
            SELECT 'INVENTORY_COUNT' as source_type, id, count_no as ref_no,
                   count_date as date, 0 as amount, 'جرد مخزني' as description,
                   journal_entry_id
            FROM inventory_counts
            WHERE status = 'POSTED' {date_clause}
        """,
    }
    
    results = []
    for stype, sql in queries.items():
        if source_type and source_type != stype:
            continue
        
        params = []
        if date_from:
            params.append(date_from)
        if date_to:
            params.append(date_to)
        
        rows = db.query(sql, params)
        for r in rows:
            row = dict(r)
            # جلب القيد
            if row.get('journal_entry_id'):
                je = db.query("""
                    SELECT entry_no, entry_date, total_debit, status
                    FROM journal_entries WHERE id = ?
                """, (row['journal_entry_id'],), one=True)
                row['journal_no'] = je['entry_no'] if je else None
                row['journal_status'] = je['status'] if je else None
            else:
                row['journal_no'] = None
                row['journal_status'] = None
            results.append(row)
    
    # رتب بالتاريخ
    results.sort(key=lambda x: x.get('date') or '', reverse=True)
    results = results[:limit]
    
    return jsonify({
        'success': True,
        'data': json_safe(results),
        'count': len(results)
    })


@cb_bp.route('/link/stats', methods=['GET'])
def linking_stats():
    """إحصائيات الترابط"""
    stats = {}
    
    # الحركات
    for stype, table, id_field in [
        ('supplier_payments', 'supplier_payments', 'payment_no'),
        ('customer_receipts', 'customer_receipts', 'receipt_no'),
        ('cash_box_transactions', 'cash_box_transactions', 'reference_no'),
        ('petty_cash_expenses', 'petty_cash_expenses', 'expense_no'),
        ('purchase_invoices', 'purchase_invoices', 'invoice_no'),
        ('sales_invoices', 'sales_invoices', 'invoice_no'),
        ('inventory_counts', 'inventory_counts', 'count_no'),      # ← جديد
        ('stock_transactions', 'stock_transactions', 'transaction_no'),  # ← جديد
    ]:
        try:
            total = db.query(f"SELECT COUNT(*) as n FROM {table}", one=True)
            linked = db.query(f"SELECT COUNT(*) as n FROM {table} WHERE journal_entry_id IS NOT NULL", one=True)
            stats[table] = {
                'total': total['n'],
                'linked': linked['n'],
                'unlinked': total['n'] - linked['n']
            }
        except:
            stats[table] = {'total': 0, 'linked': 0, 'unlinked': 0}
    
    # القيود
    try:
        je_total = db.query("SELECT COUNT(*) as n FROM journal_entries", one=True)
        je_with_ref = db.query("SELECT COUNT(*) as n FROM journal_entries WHERE reference_no IS NOT NULL", one=True)
        stats['journal_entries'] = {
            'total': je_total['n'],
            'with_reference': je_with_ref['n'],
            'without_reference': je_total['n'] - je_with_ref['n']
        }
    except:
        stats['journal_entries'] = {'total': 0, 'with_reference': 0, 'without_reference': 0}
    
    return jsonify({'success': True, 'data': stats})
