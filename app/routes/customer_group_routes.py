from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

cg_bp = Blueprint('customer_groups', __name__)


# ============================================================
# 1. إدارة المجموعات — CRUD
# ============================================================
@cg_bp.route('/', methods=['GET'])
def list_groups():
    rows = db.query("""
        SELECT cg.*,
               (SELECT COUNT(*) FROM customers WHERE group_id = cg.id) as customers_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM sales_invoices 
                WHERE customer_id IN (SELECT id FROM customers WHERE group_id = cg.id)
                  AND status = 'POSTED') as total_sales
        FROM customer_groups cg
        ORDER BY cg.id
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@cg_bp.route('/<int:gid>', methods=['GET'])
def get_group(gid):
    row = db.query("SELECT * FROM customer_groups WHERE id=?", (gid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'المجموعة غير موجودة'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@cg_bp.route('/', methods=['POST'])
def create_group():
    d = request.get_json() or {}
    if not d.get('code') or not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الكود والاسم مطلوبان'}), 400
    try:
        gid = db.execute("""
            INSERT INTO customer_groups 
            (code, name_ar, name_en, credit_days, credit_limit, discount_pct, 
             color, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (d['code'], d['name_ar'], d.get('name_en'), 
              d.get('credit_days', 30), d.get('credit_limit', 0),
              d.get('discount_pct', 0), d.get('color', '#6366f1'), d.get('notes')))
        return jsonify({'success': True, 'data': {'id': gid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@cg_bp.route('/<int:gid>', methods=['PUT'])
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
    db.execute(f"UPDATE customer_groups SET {','.join(fields)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@cg_bp.route('/<int:gid>', methods=['DELETE'])
def delete_group(gid):
    r = db.query("SELECT COUNT(*) as c FROM customers WHERE group_id=?", (gid,), one=True)
    if r['c'] > 0:
        return jsonify({'success': False, 'message': f'المجموعة مستخدمة في {r["c"]} عميل'}), 400
    db.execute("DELETE FROM customer_groups WHERE id=?", (gid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============================================================
# 2. تحديث مجموعة العميل
# ============================================================
@cg_bp.route('/assign/<int:cid>', methods=['PUT'])
def assign_customer(cid):
    d = request.get_json() or {}
    group_id = d.get('group_id')
    
    # جيب فترة الائتمان من المجموعة
    credit_days = None
    if group_id:
        g = db.query("SELECT credit_days FROM customer_groups WHERE id=?", (group_id,), one=True)
        if g:
            credit_days = g['credit_days']
    
    db.execute("""
        UPDATE customers SET group_id=?, payment_terms=? WHERE id=?
    """, (group_id, credit_days or 30, cid))
    
    return jsonify({'success': True, 'message': 'تم التحديث'})


# ============================================================
# 3. تقرير أعمار الديون (Aging Report)
# ============================================================
@cg_bp.route('/aging', methods=['GET'])
def aging_report():
    """تقرير أعمار الديون"""
    group_filter = request.args.get('group_id')
    customer_filter = request.args.get('customer_id')
    
    today = request.args.get('as_of') or __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    
    # الفلاتر
    cond = ["si.status = 'POSTED'", "si.payment_type = 'CREDIT'"]
    vals = []
    
    if group_filter:
        cond.append("c.group_id = ?")
        vals.append(int(group_filter))
    if customer_filter:
        cond.append("c.id = ?")
        vals.append(int(customer_filter))
    
    where = ' AND '.join(cond)
    
    # جيب كل فاتورة مع المدفوعات
    rows = db.query(f"""
        SELECT 
            si.id as invoice_id,
            si.invoice_no,
            si.invoice_date,
            si.total_amount,
            si.customer_id,
            c.code as customer_code,
            c.name_ar as customer_name,
            cg.name_ar as group_name,
            cg.credit_days,
            COALESCE((
                SELECT SUM(pa.amount) 
                FROM payment_allocations pa 
                WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
            ), 0) as paid_amount
        FROM sales_invoices si
        JOIN customers c ON si.customer_id = c.id
        LEFT JOIN customer_groups cg ON c.group_id = cg.id
        WHERE {where}
        ORDER BY si.invoice_date
    """, vals)
    
    # نحسب العمر
    from datetime import datetime as dt
    today_dt = dt.strptime(today, '%Y-%m-%d')
    
    # تجميع حسب العميل
    by_customer = {}
    totals = {'b0_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0, 'total': 0}
    
    for r in rows:
        remaining = float(r['total_amount']) - float(r['paid_amount'])
        if remaining <= 0.01:
            continue  # مدفوعة بالكامل
        
        inv_date = dt.strptime(r['invoice_date'], '%Y-%m-%d')
        age_days = (today_dt - inv_date).days
        
        # الفترة
        if age_days <= 30:
            bucket = 'b0_30'
        elif age_days <= 60:
            bucket = 'b31_60'
        elif age_days <= 90:
            bucket = 'b61_90'
        else:
            bucket = 'b90_plus'
        
        cid = r['customer_id']
        if cid not in by_customer:
            by_customer[cid] = {
                'customer_id': cid,
                'customer_code': r['customer_code'],
                'customer_name': r['customer_name'],
                'group_name': r['group_name'] or '—',
                'credit_days': r['credit_days'] or 30,
                'b0_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0,
                'total': 0,
                'invoices_count': 0,
            }
        
        by_customer[cid][bucket] += remaining
        by_customer[cid]['total'] += remaining
        by_customer[cid]['invoices_count'] += 1
        
        totals[bucket] += remaining
        totals['total'] += remaining
    
    # ترتيب حسب الإجمالي
    result = sorted(by_customer.values(), key=lambda x: x['total'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': result,
        'totals': totals,
        'as_of': today
    })


# ============================================================
# 4. تقرير أعمار الديون — حسب المجموعة
# ============================================================
@cg_bp.route('/aging-by-group', methods=['GET'])
def aging_by_group():
    """تقرير أعمار الديون — مجمّع حسب المجموعة"""
    today = request.args.get('as_of') or __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    
    rows = db.query("""
        SELECT 
            si.id as invoice_id,
            si.invoice_date,
            si.total_amount,
            c.id as customer_id,
            cg.id as group_id,
            cg.code as group_code,
            cg.name_ar as group_name,
            cg.color as group_color,
            COALESCE((
                SELECT SUM(pa.amount) 
                FROM payment_allocations pa 
                WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
            ), 0) as paid_amount
        FROM sales_invoices si
        JOIN customers c ON si.customer_id = c.id
        LEFT JOIN customer_groups cg ON c.group_id = cg.id
        WHERE si.status = 'POSTED' AND si.payment_type = 'CREDIT'
    """)
    
    from datetime import datetime as dt
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
                'customers': set(),
            }
        
        by_group[gid][bucket] += remaining
        by_group[gid]['total'] += remaining
        by_group[gid]['customers'].add(r['customer_id'])
    
    # تحويل set لعدد
    result = []
    for g in by_group.values():
        g['customers_count'] = len(g['customers'])
        del g['customers']
        result.append(g)
    
    result.sort(key=lambda x: x['total'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': result,
        'as_of': today
    })
