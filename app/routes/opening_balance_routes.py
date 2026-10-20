from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from datetime import datetime

ob_bp = Blueprint('opening_balances', __name__)


# ============================================================
# 1. جيب شجرة الحسابات — مع فلتر المستوى
# ============================================================
@ob_bp.route('/accounts-tree', methods=['GET'])
def accounts_tree():
    """جيب كل الحسابات الأب مع عدد الأبناء + فلتر المستوى"""
    
    level = request.args.get('level', '')
    
    cond = """
        a.code IN (
            SELECT DISTINCT parent_code FROM accounts 
            WHERE parent_code IS NOT NULL AND parent_code != ''
        )
        AND a.is_active = 1
    """
    vals = []
    
    if level:
        cond += " AND a.level = ?"
        vals.append(level)
    
    rows = db.query(f"""
        SELECT 
            a.code,
            a.name_ar,
            a.level,
            a.nature,
            a.is_leaf,
            (SELECT COUNT(*) FROM accounts WHERE parent_code = a.code) as children_count
        FROM accounts a
        WHERE {cond}
        ORDER BY a.level, a.code
    """, vals)
    
    # إحصائيات
    stats = db.query(f"""
        SELECT 
            a.level,
            COUNT(*) as count
        FROM accounts a
        WHERE {cond}
        GROUP BY a.level
        ORDER BY a.level
    """, vals)
    
    return jsonify({
        'success': True, 
        'data': json_safe(rows),
        'stats': json_safe(stats)
    })


# ============================================================
# 2. جيب كل المستويات المتاحة
# ============================================================
@ob_bp.route('/levels', methods=['GET'])
def get_levels():
    """جيب كل المستويات المتاحة"""
    rows = db.query("""
        SELECT DISTINCT level, COUNT(*) as count
        FROM accounts
        WHERE code IN (
            SELECT DISTINCT parent_code FROM accounts 
            WHERE parent_code IS NOT NULL AND parent_code != ''
        )
        AND is_active = 1
        GROUP BY level
        ORDER BY level
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


# ============================================================
# 3. جيب الأبناء المباشرين لحساب معين
# ============================================================
@ob_bp.route('/children/<path:code>', methods=['GET'])
def get_children(code):
    """جيب كل الحسابات الورقية تحت حساب معين (بشكل هرمي)"""
    
    parent = db.query("SELECT code, name_ar, level FROM accounts WHERE code=?", (code,), one=True)
    if not parent:
        return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 404
    
    def get_all_descendants(parent_code):
        result = []
        children = db.query("""
            SELECT code, name_ar, level, is_leaf, nature 
            FROM accounts 
            WHERE parent_code = ? AND is_active = 1
            ORDER BY code
        """, (parent_code,))
        
        for c in children:
            c = dict(c)
            if c['is_leaf']:
                result.append(c)
            else:
                result.extend(get_all_descendants(c['code']))
        
        return result
    
    leaves = get_all_descendants(code)
    
    # جيب الأرصدة الافتتاحية
    existing = {}
    if leaves:
        codes = [l['code'] for l in leaves]
        placeholders = ','.join(['?'] * len(codes))
        balances = db.query(f"""
            SELECT * FROM opening_balances
            WHERE account_code IN ({placeholders})
        """, codes)
        
        for b in balances:
            existing[b['account_code']] = dict(b)
    
    result = []
    for leaf in leaves:
        b = existing.get(leaf['code'])
        row = {
            'account_code': leaf['code'],
            'account_name': leaf['name_ar'],
            'level': leaf['level'],
            'nature': leaf['nature'],
            'debit': 0,
            'credit': 0,
            'opening_id': None,
            'document_no': '',
            'document_type': 'رصيد افتتاحي',
            'document_date': datetime.now().strftime('%Y-%m-%d'),
            'notes': '',
            'is_posted': 0,
            'journal_entry_id': None,
        }
        
        if b:
            row['opening_id'] = b['id']
            row['document_no'] = b.get('document_no') or ''
            row['document_type'] = b.get('document_type') or 'رصيد افتتاحي'
            row['document_date'] = b.get('document_date') or ''
            row['notes'] = b.get('notes') or ''
            row['is_posted'] = b['is_posted']
            row['journal_entry_id'] = b['journal_entry_id']
            
            if b['direction'] == 'DEBIT':
                row['debit'] = float(b['amount'])
            else:
                row['credit'] = float(b['amount'])
        
        result.append(row)
    
    return jsonify({
        'success': True,
        'parent': json_safe(parent),
        'data': json_safe(result),
        'count': len(result),
    })


# ============================================================
# 4. حفظ جماعي
# ============================================================
@ob_bp.route('/save-batch', methods=['POST'])
def save_batch():
    d = request.get_json() or {}
    parent_code = d.get('parent_code')
    rows = d.get('rows', [])
    
    if not parent_code:
        return jsonify({'success': False, 'message': 'parent_code مطلوب'}), 400
    
    if not rows:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    saved = 0
    errors = []
    
    try:
        for row in rows:
            acc_code = row.get('account_code')
            debit = float(row.get('debit', 0) or 0)
            credit = float(row.get('credit', 0) or 0)
            
            if not acc_code:
                continue
            
            if debit == 0 and credit == 0:
                existing = db.query("""
                    SELECT id, is_posted FROM opening_balances WHERE account_code=?
                """, (acc_code,), one=True)
                if existing and not existing['is_posted']:
                    db.execute("DELETE FROM opening_balances WHERE id=?", (existing['id'],))
                continue
            
            if debit > 0 and credit > 0:
                errors.append(f"{acc_code}: لا يمكن إدخال مدين ودائن معاً")
                continue
            
            amount = debit if debit > 0 else credit
            direction = 'DEBIT' if debit > 0 else 'CREDIT'
            
            doc_no = row.get('document_no') or ''
            doc_type = row.get('document_type') or 'رصيد افتتاحي'
            doc_date = row.get('document_date') or datetime.now().strftime('%Y-%m-%d')
            notes = row.get('notes') or ''
            
            acc = db.query("SELECT name_ar FROM accounts WHERE code=?", (acc_code,), one=True)
            acc_name = acc['name_ar'] if acc else ''
            
            party_type = 'ACCOUNT'
            party_code = acc_code
            party_name = acc_name
            
            if acc_code.startswith('1221'):
                party_type = 'CUSTOMER'
                cust = db.query("SELECT code, name_ar FROM customers WHERE account_code=?", (acc_code,), one=True)
                if cust:
                    party_code = cust['code']
                    party_name = cust['name_ar']
            elif acc_code.startswith('2211'):
                party_type = 'SUPPLIER'
                supp = db.query("SELECT code, name_ar FROM suppliers WHERE account_code=?", (acc_code,), one=True)
                if supp:
                    party_code = supp['code']
                    party_name = supp['name_ar']
            
            existing = db.query("""
                SELECT id, is_posted FROM opening_balances WHERE account_code=?
            """, (acc_code,), one=True)
            
            if existing:
                if existing['is_posted']:
                    errors.append(f"{acc_code}: مُرحّل")
                    continue
                
                db.execute("""
                    UPDATE opening_balances SET
                        amount=?, direction=?,
                        document_no=?, document_type=?, document_date=?,
                        party_type=?, party_code=?, party_name=?, account_name=?, notes=?
                    WHERE id=?
                """, (amount, direction, doc_no, doc_type, doc_date,
                      party_type, party_code, party_name, acc_name, notes, existing['id']))
            else:
                db.execute("""
                    INSERT INTO opening_balances
                    (account_code, party_type, party_code, party_name, account_name,
                     amount, direction, document_no, document_type, document_date, notes,
                     is_posted, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (acc_code, party_type, party_code, party_name, acc_name,
                      amount, direction, doc_no, doc_type, doc_date, notes,
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            saved += 1
        
        return jsonify({
            'success': True,
            'message': f'تم حفظ {saved} رصيد',
            'saved': saved,
            'errors': errors,
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# ============================================================
# 5. ترحيل الكل
# ============================================================
@ob_bp.route('/post-all/<path:parent_code>', methods=['POST'])
def post_all(parent_code):
    rows = db.query("""
        SELECT * FROM opening_balances
        WHERE account_code LIKE ? || '%'
          AND is_posted = 0
          AND amount > 0
    """, (parent_code,))
    
    if not rows:
        return jsonify({'success': False, 'message': 'لا توجد أرصدة للترحيل'}), 400
    
    posted = 0
    errors = []
    
    for row in rows:
        try:
            row = dict(row)
            amount = float(row['amount'])
            direction = row['direction']
            acc_code = row['account_code']
            
            count = db.query("SELECT COUNT(*)+1 as n FROM journal_entries", one=True)['n']
            entry_no = f"JE-{datetime.now().year}-{count:06d}"
            
            je_id = db.execute("""
                INSERT INTO journal_entries
                (entry_no, entry_date, reference_type, reference_no, description,
                 total_debit, total_credit, status, created_at, created_by)
                VALUES (?, ?, 'OPENING_BALANCE', ?, ?, ?, ?, 'POSTED', ?, 1)
            """, (entry_no, row.get('document_date') or datetime.now().strftime('%Y-%m-%d'),
                  row.get('document_no') or acc_code,
                  f"رصيد افتتاحي - {row.get('account_name', acc_code)}",
                  amount, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            if direction == 'DEBIT':
                db.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 1, ?, 'رصيد افتتاحي - مدين', ?, 0)
                """, (je_id, acc_code, amount))
                
                db.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 2, '3302', 'رصيد افتتاحي', 0, ?)
                """, (je_id, amount))
            else:
                db.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 1, '3302', 'رصيد افتتاحي', ?, 0)
                """, (je_id, amount))
                
                db.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 2, ?, 'رصيد افتتاحي - دائن', 0, ?)
                """, (je_id, acc_code, amount))
            
            db.execute("""
                UPDATE opening_balances SET is_posted=1, journal_entry_id=? WHERE id=?
            """, (je_id, row['id']))
            
            posted += 1
        
        except Exception as e:
            errors.append(f"{row.get('account_code')}: {e}")
    
    return jsonify({
        'success': True,
        'message': f'تم ترحيل {posted} رصيد',
        'posted': posted,
        'errors': errors,
    })
