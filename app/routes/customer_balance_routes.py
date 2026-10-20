from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

cust_balance_bp = Blueprint('customer_balances', __name__)


@cust_balance_bp.route('/balances', methods=['GET'])
def customer_balances():
    """أرصدة كل العملاء"""
    only_with_balance = request.args.get('only_with_balance', '1') == '1'
    
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                c.id,
                c.code,
                c.name_ar,
                c.phone,
                c.credit_limit,
                
                -- إجمالي الفواتير المرحّلة
                COALESCE((
                    SELECT SUM(si.total_amount)
                    FROM sales_invoices si
                    WHERE si.customer_id = c.id AND si.status = 'POSTED'
                ), 0) as total_invoiced,
                
                -- إجمالي المحصّل
                COALESCE((
                    SELECT SUM(cr.amount)
                    FROM customer_receipts cr
                    WHERE cr.customer_id = c.id AND cr.status = 'POSTED'
                ), 0) as total_paid,
                
                -- عدد الفواتير المفتوحة
                COALESCE((
                    SELECT COUNT(*)
                    FROM sales_invoices si
                    WHERE si.customer_id = c.id 
                      AND si.status = 'POSTED'
                      AND si.payment_type = 'CREDIT'
                      AND si.total_amount > COALESCE((
                          SELECT SUM(pa.amount) FROM payment_allocations pa
                          WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
                      ), 0)
                ), 0) as open_invoices_count
                
            FROM customers c
            WHERE c.is_active = 1
            ORDER BY c.code
        """).fetchall()
    
    result = []
    totals = {'total_invoiced': 0, 'total_paid': 0, 'total_balance': 0}
    
    for r in rows:
        balance = float(r['total_invoiced']) - float(r['total_paid'])
        
        if only_with_balance and abs(balance) < 0.01:
            continue
        
        totals['total_invoiced'] += float(r['total_invoiced'])
        totals['total_paid'] += float(r['total_paid'])
        totals['total_balance'] += balance
        
        result.append({
            'id': r['id'],
            'code': r['code'],
            'name_ar': r['name_ar'],
            'phone': r['phone'],
            'credit_limit': float(r['credit_limit'] or 0),
            'total_invoiced': float(r['total_invoiced']),
            'total_paid': float(r['total_paid']),
            'balance': balance,
            'open_invoices_count': r['open_invoices_count']
        })
    
    return jsonify({
        'success': True,
        'data': result,
        'totals': totals
    })


@cust_balance_bp.route('/statement/<int:customer_id>', methods=['GET'])
def customer_statement(customer_id):
    """كشف حساب عميل"""
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    
    with db.get_connection() as conn:
        # بيانات العميل
        cust = conn.execute(
            "SELECT * FROM customers WHERE id=?",
            (customer_id,)
        ).fetchone()
        
        if not cust:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        
        # الفواتير
        inv_sql = "SELECT id, invoice_no, invoice_date, total_amount, status, payment_type FROM sales_invoices WHERE customer_id=?"
        inv_params = [customer_id]
        if df:
            inv_sql += " AND invoice_date >= ?"
            inv_params.append(df)
        if dt:
            inv_sql += " AND invoice_date <= ?"
            inv_params.append(dt)
        inv_sql += " ORDER BY invoice_date"
        
        invoices = [dict(r) for r in conn.execute(inv_sql, inv_params).fetchall()]
        
        # التحصيلات
        rec_sql = "SELECT id, receipt_no, receipt_date, amount, receipt_method FROM customer_receipts WHERE customer_id=?"
        rec_params = [customer_id]
        if df:
            rec_sql += " AND receipt_date >= ?"
            rec_params.append(df)
        if dt:
            rec_sql += " AND receipt_date <= ?"
            rec_params.append(dt)
        rec_sql += " ORDER BY receipt_date"
        
        receipts = [dict(r) for r in conn.execute(rec_sql, rec_params).fetchall()]
        
        # الفواتير المفتوحة
        open_inv = [dict(r) for r in conn.execute("""
            SELECT 
                si.id, si.invoice_no, si.invoice_date, si.total_amount,
                COALESCE((
                    SELECT SUM(pa.amount) FROM payment_allocations pa
                    WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
                ), 0) as paid_amount,
                si.total_amount - COALESCE((
                    SELECT SUM(pa.amount) FROM payment_allocations pa
                    WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
                ), 0) as remaining
            FROM sales_invoices si
            WHERE si.customer_id = ?
              AND si.status = 'POSTED'
              AND si.payment_type = 'CREDIT'
              AND si.total_amount > COALESCE((
                  SELECT SUM(pa.amount) FROM payment_allocations pa
                  WHERE pa.invoice_id = si.id AND pa.invoice_type = 'SALES'
              ), 0)
            ORDER BY si.invoice_date
        """, (customer_id,)).fetchall()]
    
    total_invoiced = sum(float(i['total_amount']) for i in invoices)
    total_paid = sum(float(r['amount']) for r in receipts)
    
    return jsonify({
        'success': True,
        'data': {
            'customer': dict(cust),
            'invoices': invoices,
            'receipts': receipts,
            'open_invoices': open_inv,
            'totals': {
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'balance': total_invoiced - total_paid
            }
        }
    })