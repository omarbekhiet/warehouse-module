from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

supp_balance_bp = Blueprint('supplier_balances', __name__)


@supp_balance_bp.route('/balances', methods=['GET'])
def supplier_balances():
    """أرصدة كل الموردين"""
    only_with_balance = request.args.get('only_with_balance', '1') == '1'
    
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                s.id,
                s.code,
                s.name_ar,
                s.name_en,
                s.phone,
                s.email,
                s.address,
                s.tax_number,
                s.payment_terms,
                s.is_active,
                s.notes,
                
                COALESCE((
                    SELECT SUM(pi.total_amount)
                    FROM purchase_invoices pi
                    WHERE pi.supplier_id = s.id AND pi.status = 'POSTED'
                ), 0) as total_invoiced,
                
                COALESCE((
                    SELECT SUM(sp.amount)
                    FROM supplier_payments sp
                    WHERE sp.supplier_id = s.id AND sp.status = 'POSTED'
                ), 0) as total_paid,
                
                COALESCE((
                    SELECT COUNT(*)
                    FROM purchase_invoices pi
                    WHERE pi.supplier_id = s.id 
                      AND pi.status = 'POSTED'
                      AND pi.payment_type = 'CREDIT'
                      AND pi.total_amount > COALESCE((
                          SELECT SUM(pa.amount) FROM payment_allocations pa
                          WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
                      ), 0)
                ), 0) as open_invoices_count
                
            FROM suppliers s
            WHERE s.is_active = 1
            ORDER BY s.code
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
            'name_en': r['name_en'],
            'phone': r['phone'],
            'email': r['email'],
            'address': r['address'],
            'tax_number': r['tax_number'],
            'payment_terms': r['payment_terms'],
            'is_active': r['is_active'],
            'notes': r['notes'],
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


@supp_balance_bp.route('/statement/<int:supplier_id>', methods=['GET'])
def supplier_statement(supplier_id):
    """كشف حساب مورد"""
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    
    with db.get_connection() as conn:
        supp = conn.execute(
            "SELECT * FROM suppliers WHERE id=?",
            (supplier_id,)
        ).fetchone()
        
        if not supp:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        
        # الفواتير
        inv_sql = "SELECT id, invoice_no, invoice_date, total_amount, status, payment_type FROM purchase_invoices WHERE supplier_id=?"
        inv_params = [supplier_id]
        if df:
            inv_sql += " AND invoice_date >= ?"
            inv_params.append(df)
        if dt:
            inv_sql += " AND invoice_date <= ?"
            inv_params.append(dt)
        inv_sql += " ORDER BY invoice_date"
        
        invoices = [dict(r) for r in conn.execute(inv_sql, inv_params).fetchall()]
        
        # المدفوعات
        pay_sql = "SELECT id, payment_no, payment_date, amount, payment_method FROM supplier_payments WHERE supplier_id=?"
        pay_params = [supplier_id]
        if df:
            pay_sql += " AND payment_date >= ?"
            pay_params.append(df)
        if dt:
            pay_sql += " AND payment_date <= ?"
            pay_params.append(dt)
        pay_sql += " ORDER BY payment_date"
        
        payments = [dict(r) for r in conn.execute(pay_sql, pay_params).fetchall()]
        
        # الفواتير المفتوحة
        open_inv = [dict(r) for r in conn.execute("""
            SELECT 
                pi.id, pi.invoice_no, pi.invoice_date, pi.total_amount,
                COALESCE((
                    SELECT SUM(pa.amount) FROM payment_allocations pa
                    WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
                ), 0) as paid_amount,
                pi.total_amount - COALESCE((
                    SELECT SUM(pa.amount) FROM payment_allocations pa
                    WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
                ), 0) as remaining
            FROM purchase_invoices pi
            WHERE pi.supplier_id = ?
              AND pi.status = 'POSTED'
              AND pi.payment_type = 'CREDIT'
              AND pi.total_amount > COALESCE((
                  SELECT SUM(pa.amount) FROM payment_allocations pa
                  WHERE pa.invoice_id = pi.id AND pa.invoice_type = 'PURCHASE'
              ), 0)
            ORDER BY pi.invoice_date
        """, (supplier_id,)).fetchall()]
    
    total_invoiced = sum(float(i['total_amount']) for i in invoices)
    total_paid = sum(float(p['amount']) for p in payments)
    
    return jsonify({
        'success': True,
        'data': {
            'supplier': dict(supp),
            'invoices': invoices,
            'payments': payments,
            'open_invoices': open_inv,
            'totals': {
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'balance': total_invoiced - total_paid
            }
        }
    })