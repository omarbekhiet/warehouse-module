from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, enrich_with_user

account_bp = Blueprint('accounts', __name__)




# ============================================================
# دالة التحقق الشاملة من صحة الحساب
# ============================================================
def validate_account_data(data, exclude_code=None):
    """يرجّع (errors_list, warnings_list)"""
    errors = []
    warnings = []
    
    code = (data.get('code') or '').strip()
    name_ar = (data.get('name_ar') or '').strip()
    level = data.get('level') or 'L5'
    parent_code = (data.get('parent_code') or '').strip() or None
    nature = data.get('nature') or 'D'
    is_leaf = data.get('is_leaf', 1)
    
    # 1) الكود مطلوب
    if not code:
        errors.append('الكود مطلوب')
        return errors, warnings
    
    # 2) الاسم مطلوب
    if not name_ar:
        errors.append('الاسم بالعربي مطلوب')
    
    # 3) الكود المكرر
    existing = db.query(
        "SELECT code, name_ar FROM accounts WHERE code = ?",
        (code,), one=True
    )
    if existing and (exclude_code is None or existing['code'] != exclude_code):
        errors.append(f'الكود "{code}" موجود بالفعل لحساب: {existing["name_ar"]}')
    
    # 4) طول الكود حسب المستوى
    level_num = int((level or 'L1').replace('L', ''))
    code_len = len(code)
    expected_ranges = {
        1: (1, 1),
        2: (2, 2),
        3: (3, 4),
        4: (5, 6),
        5: (7, 10),
    }
    if level_num in expected_ranges:
        min_len, max_len = expected_ranges[level_num]
        if code_len < min_len or code_len > max_len:
            warnings.append(
                f'طول الكود ({code_len}) لا يتناسب مع المستوى {level} '
                f'(المتوقع: {min_len}-{max_len} رقم)'
            )
    
    # 5) التحقق من الأب
    if parent_code:
        parent = db.query(
            "SELECT * FROM accounts WHERE code = ?",
            (parent_code,), one=True
        )
        
        if not parent:
            errors.append(f'الحساب الأب "{parent_code}" غير موجود')
        else:
            # 5.1) الأب مش مسموح له قيود
            if parent.get('has_entries') == 1:
                errors.append(
                    f'لا يمكن إضافة حساب فرعي: الحساب الأب "{parent["name_ar"]}" '
                    f'له {parent.get("entries_count", 0)} قيد محاسبي'
                )
            
            # 5.2) الأب لازم يكون أعلى
            parent_level_num = int((parent.get('level') or 'L1').replace('L', ''))
            if parent_level_num >= level_num:
                errors.append(
                    f'مستوى الأب ({parent["level"]}) لازم يكون أعلى من مستوى الابن ({level})'
                )
            
            # 5.3) الأب مش L5
            if parent_level_num == 5:
                errors.append('لا يمكن إضافة حساب فرعي تحت مستوى L5')
            
            # 5.4) الطبيعة متوافقة
            parent_nature = parent.get('nature')
            if parent_nature and nature and parent_nature != nature:
                warnings.append(
                    f'الطبيعة مختلفة عن الأب: الأب={parent_nature}، الابن={nature}'
                )
    else:
        if level_num > 1:
            warnings.append(f'حساب بدون أب عادةً L1، لكنك اخترت {level}')
    
    return errors, warnings


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
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@account_bp.route('/leaf', methods=['GET'])
def list_leaf():
    rows = db.query("SELECT * FROM accounts WHERE is_leaf=1 AND is_active=1 ORDER BY code")
    rows = enrich_with_user(rows)
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
    """إنشاء حساب جديد"""
    data = request.get_json() or {}
    
    # التحقق الشامل
    errors, warnings = validate_account_data(data)
    if errors:
        return jsonify({
            'success': False,
            'message': errors[0],
            'errors': errors,
            'warnings': warnings
        }), 400
    
    # لو فيه warnings، نرجعها مع النجاح
    try:
        db.execute("""
            INSERT INTO accounts 
            (code, name_ar, name_en, level, nature, parent_code,
             financial_statement, bs_group, pl_group, is_group, is_leaf,
             ifrs18_category, ifrs18_subcategory, ifrs18_statement, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            data.get('code'), data.get('name_ar'), data.get('name_en'),
            data.get('level'), data.get('nature'), data.get('parent_code'),
            data.get('financial_statement'), data.get('bs_group'), data.get('pl_group'),
            data.get('is_group', 0), data.get('is_leaf', 1),
            data.get('ifrs18_category'), data.get('ifrs18_subcategory'),
            data.get('ifrs18_statement')
        ))
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الحساب بنجاح',
            'warnings': warnings
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الحفظ: {str(e)[:100]}'
        }), 500


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


@account_bp.route('/<int:acc_id>', methods=['DELETE'])
def delete_account(acc_id):
    """حذف حساب"""
    acc = db.query("SELECT * FROM accounts WHERE id = ?", (acc_id,), one=True)
    if not acc:
        return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 404
    
    # 1) التحقق من القيود
    if acc.get('has_entries') == 1:
        return jsonify({
            'success': False,
            'message': f'لا يمكن حذف الحساب "{acc["name_ar"]}": مستخدم في {acc.get("entries_count", 0)} قيد محاسبي'
        }), 400
    
    # 2) التحقق من الأبناء
    children = db.query(
        "SELECT COUNT(*) as c FROM accounts WHERE parent_code = ?",
        (acc['code'],), one=True
    )
    if children and children['c'] > 0:
        return jsonify({
            'success': False,
            'message': f'لا يمكن حذف الحساب "{acc["name_ar"]}": لديه {children["c"]} حساب فرعي'
        }), 400
    
    # 3) الحذف
    try:
        db.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        return jsonify({'success': True, 'message': 'تم الحذف'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)[:100]}), 500


@account_bp.route('/types', methods=['GET'])
def list_types():
    rows = db.query("SELECT * FROM account_types ORDER BY code")
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})


@account_bp.route('/by-category/<category>', methods=['GET'])
def accounts_by_category(category):
    """
    جلب الحسابات حسب التصنيف
    
    Categories:
    - inventory    → حسابات المخزون (123x)
    - cost         → حسابات التكلفة (5xxx, 6xxx)
    - revenue      → حسابات الإيراد (4xxx)
    - expense      → المصروفات (5xxx)
    - cogs         → تكلفة النشاط (6xxx)
    - asset        → الأصول (1xxx)
    - liability    → الالتزامات (2xxx)
    - equity       → حقوق الملكية (3xxx)
    - tax          → الضرائب (8xxx)
    - clearing     → الحسابات الوسيطة (حسب الكود اللي فيه clearing)
    - all          → كل الحسابات (leaf فقط)
    """
    # تحديد نطاق الأكواد حسب التصنيف
    category_prefixes = {
        'inventory': ['123'],          # مخزون
        'cost': ['5', '6'],            # مصروفات + تكلفة
        'revenue': ['4'],              # إيرادات
        'expense': ['5'],              # مصروفات
        'cogs': ['6'],                 # تكلفة النشاط
        'asset': ['1'],                # أصول
        'liability': ['2'],            # التزامات
        'equity': ['3'],               # حقوق ملكية
        'tax': ['8'],                  # ضرائب
        'investing': ['72', '73'],     # استثمار
        'financing': ['71'],           # تمويل
        'clearing': ['1232'],          # وسيطة (مخزون وسيط)
        'all': [],                     # كل شيء
    }
    
    prefixes = category_prefixes.get(category, [])
    
    if category == 'clearing':
        # الحسابات الوسيطة (1232x)
        rows = db.query("""
            SELECT code, name_ar, level, nature, ifrs18_category, 
                   ifrs18_subcategory, ifrs18_statement
            FROM accounts 
            WHERE is_leaf = 1 
              AND is_active = 1
              AND code LIKE '1232%'
            ORDER BY code
        """)
    elif category == 'all' or not prefixes:
        # كل الحسابات
        rows = db.query("""
            SELECT code, name_ar, level, nature, ifrs18_category,
                   ifrs18_subcategory, ifrs18_statement
            FROM accounts 
            WHERE is_leaf = 1 
              AND is_active = 1
            ORDER BY code
        """)
    else:
        # نبني شرط البحث
        where_parts = []
        for p in prefixes:
            where_parts.append(f"code LIKE '{p}%'")
        where_sql = " OR ".join(where_parts)
        
        rows = db.query(f"""
            SELECT code, name_ar, level, nature, ifrs18_category,
                   ifrs18_subcategory, ifrs18_statement
            FROM accounts 
            WHERE is_leaf = 1 
              AND is_active = 1
              AND ({where_sql})
            ORDER BY code
        """)
    
    return jsonify({
        'success': True,
        'category': category,
        'count': len(rows),
        'data': json_safe(rows)
    })
