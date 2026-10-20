from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

sg_bp = Blueprint('supplier_groups', __name__)


# ============================================================
# 1. إدارة المجموعات — CRUD
# ============================================================
@sg_bp.route('/', methods=['GET'])
def list_groups():
    rows = db.query("""
        SELECT sg.*,
               (SELECT COUNT(*) FROM suppliers WHERE group_id = sg.id) as suppliers_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM purchase_invoices 
                WHERE supplier_id IN (SELECT id FROM suppliers WHERE group_id = sg.id)
                  AND status = 'POSTED') as total_purchases
        FROM supplier_groups sg
        ORDER BY sg.id
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@sg_bp.route('/<int:gid>', methods=['GET'])
def get_group(gid):
    row = db.query("SELECT * FROM supplier_groups WHERE id=?", (gid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'المجموعة غير موجودة'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@sg_bp.route('/', methods=['POST'])
def create_group():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        gid = db.execute("""
            INSERT INTO supplier_groups 
            (code, name_ar, name_en, credit_days, credit_limit, discount_pct, 
             color, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (d['code'], d['name_ar'], d.get('name_en'), 
              d.get('credit_days', 30), d.get('credit_limit', 0),
              d.get('discount_pct', 0), d.get('color', '#6366f1'), d.get('notes')))
        return jsonify({'success': True, 'data': {'id': gid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@sg_bp.route('/<int:gid>', methods=['PUT'])
def update_group(gid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['code', 'name_ar', 'name_en', 'credit_days', 'credit_limit', 
              'discount_pct', 'color', 'notes', 'is_active']:
        if k in d:
            fields.append(f"{k}=?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(gid)
    db.execute(f"UPDATE supplier_groups SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@sg_bp.route('/<int:gid>', methods=['DELETE'])
def delete_group(gid):
    r = db.query("SELECT COUNT(*) as c FROM suppliers WHERE group_id=?", (gid,), one=True)
    if r['c'] > 0:
        return jsonify({'success': False, 'message': f'المجموعة مستخدمة في {r["c"]} مورد'}), 400
    db.execute("DELETE FROM supplier_groups WHERE id=?", (gid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============================================================
# 2. تقرير أعمار الديون — للموردين (Aging Report)
# ============================================================
@sg_bp.route('/aging', methods=['GET'])
def aging_report():
    """تقرير أعمار الديون للموردين"""
    group_filter = request.args.get('group_id')
    supplier_filter = request.args.get('supplier_id')
    
    from datetime import datetime as dt
    today = request.args.get('as_of') or dt.now().strftime('%Y-%m-%d')
    
    # الفلاتر
    cond = ["pi.status = 'POSTED'", "pi.payment_type = 'CREDIT'"]
    vals = []
    
    if group_filter:
        cond.append("s.group_id = ?")
        vals.append(int(group_filter))
    if supplier_filter:
        cond.append("s.id = ?")
        vals.append(int(supplier_filter))
    
    where = ' AND '.join(cond)
    
    # جيب كل فاتورة مع المدفوعات
    rows = db.query(f"""
        SELECT 
            pi.id as invoice_id,
            pi.invoice_no,
            pi.invoice_date,
            pi.total_amount,
            pi.supplier_id,
            s.code as supplier_code,
            s.name_ar as supplier_name,
            sg.name_ar as group_name,
            sg.color as group_color,
            sg.credit_days,
            COALESCE((
                SELECT SUM(pa.amount) 
                FROM payment_allocations pa 
                WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
            ), 0) as paid_amount
        FROM purchase_invoices pi
        JOIN suppliers s ON pi.supplier_id = s.id
        LEFT JOIN supplier_groups sg ON s.group_id = sg.id
        WHERE {where}
        ORDER BY pi.invoice_date
    """, vals)
    
    # نحسب العمر
    today_dt = dt.strptime(today, '%Y-%m-%d')
    
    by_supplier = {}
    totals = {'b0_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0, 'total': 0}
    
    for r in rows:
        remaining = float(r['total_amount']) - float(r['paid_amount'])
        if remaining <= 0.01:
            continue
        
        inv_date = dt.strptime(r['invoice_date'], '%Y-%m-%d')
        age_days = (today_dt - inv_date).days
        
        if age_days <= 30:
            bucket = 'b0_30'
        elif age_days <= 60:
            bucket = 'b31_60'
        elif age_days <= 90:
            bucket = 'b61_90'
        else:
            bucket = 'b90_plus'
        
        sid = r['supplier_id']
        if sid not in by_supplier:
            by_supplier[sid] = {
                'supplier_id': sid,
                'supplier_code': r['supplier_code'],
                'supplier_name': r['supplier_name'],
                'group_name': r['group_name'] or '—',
                'group_color': r['group_color'] or '#64748b',
                'credit_days': r['credit_days'] or 30,
                'b0_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0,
                'total': 0,
                'invoices_count': 0,
            }
        
        by_supplier[sid][bucket] += remaining
        by_supplier[sid]['total'] += remaining
        by_supplier[sid]['invoices_count'] += 1
        
        totals[bucket] += remaining
        totals['total'] += remaining
    
    result = sorted(by_supplier.values(), key=lambda x: x['total'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': result,
        'totals': totals,
        'as_of': today
    })


# ============================================================
# 3. تقرير أعمار الديون — حسب المجموعة
# ============================================================
@sg_bp.route('/aging-by-group', methods=['GET'])
def aging_by_group():
    """تقرير أعمار الديون — مجمّع حسب المجموعة"""
    from datetime import datetime as dt
    today = request.args.get('as_of') or dt.now().strftime('%Y-%m-%d')
    
    rows = db.query("""
        SELECT 
            pi.id as invoice_id,
            pi.invoice_date,
            pi.total_amount,
            s.id as supplier_id,
            sg.id as group_id,
            sg.code as group_code,
            sg.name_ar as group_name,
            sg.color as group_color,
            COALESCE((
                SELECT SUM(pa.amount) 
                FROM payment_allocations pa 
                WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
            ), 0) as paid_amount
        FROM purchase_invoices pi
        JOIN suppliers s ON pi.supplier_id = s.id
        LEFT JOIN supplier_groups sg ON s.group_id = sg.id
        WHERE pi.status = 'POSTED' AND pi.payment_type = 'CREDIT'
    """)
    
    today_dt = dt.strptime(today, '%Y-%m-%d')
    
    by_group = {}
    for r in rows:
        remaining = float(r['total_amount']) - float(r['paid_amount'])
        if remaining <= 0.01:
            continue
        
        inv_date = dt.strptime(r['invoice_date'], '%Y-%m-%d')
        age = (today_dt - inv_date).days
        
        if age <= 30:
            bucket = 'b0_30'
        elif age <= 60:
            bucket = 'b31_60'
        elif age <= 90:
            bucket = 'b61_90'
        else:
            bucket = 'b90_plus'
        
        gid = r['group_id'] or 0
        if gid not in by_group:
            by_group[gid] = {
                'group_id': gid,
                'group_code': r['group_code'] or '—',
                'group_name': r['group_name'] or 'بدون مجموعة',
                'group_color': r['group_color'] or '#94a3b8',
                'b0_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0,
                'total': 0,
                'suppliers': set(),
            }
        
        by_group[gid][bucket] += remaining
        by_group[gid]['total'] += remaining
        by_group[gid]['suppliers'].add(r['supplier_id'])
    
    result = []
    for g in by_group.values():
        g['suppliers_count'] = len(g['suppliers'])
        del g['suppliers']
        result.append(g)
    
    result.sort(key=lambda x: x['total'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': result,
        'as_of': today
    })
