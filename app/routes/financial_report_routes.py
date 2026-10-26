from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

fin_bp = Blueprint('financial_reports', __name__)


def _get_balance_per_account(conn, date_from=None, date_to=None):
    cond, vals = [], []
    if date_from:
        cond.append('je.entry_date >= ?'); vals.append(date_from)
    if date_to:
        cond.append('je.entry_date <= ?'); vals.append(date_to)
    where = ('WHERE ' + ' AND '.join(cond)) if cond else ''
    
    rows = conn.execute(f"""
        SELECT 
            a.code, a.name_ar, a.level, a.nature, a.financial_statement,
            a.bs_group, a.pl_group, a.is_leaf,
            COALESCE(SUM(jel.debit_amount), 0) as total_debit,
            COALESCE(SUM(jel.credit_amount), 0) as total_credit
        FROM accounts a
        LEFT JOIN journal_entry_lines jel ON jel.account_code = a.code
        LEFT JOIN journal_entries je ON jel.journal_entry_id = je.id
        {where}
        GROUP BY a.code
        ORDER BY a.code
    """, vals).fetchall()
    
    return [dict(r) for r in rows]


@fin_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)
    
    result = []
    total_debit = 0
    total_credit = 0
    
    for a in accounts:
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        if td == 0 and tc == 0:
            continue
        
        if a['nature'] in ('D',):
            balance = td - tc
            debit_col = balance if balance > 0 else 0
            credit_col = abs(balance) if balance < 0 else 0
        else:
            balance = tc - td
            credit_col = balance if balance > 0 else 0
            debit_col = abs(balance) if balance < 0 else 0
        
        result.append({
            'code': a['code'], 'name_ar': a['name_ar'], 'level': a['level'],
            'nature': a['nature'], 'total_debit': td, 'total_credit': tc,
            'debit_balance': round(debit_col, 2), 'credit_balance': round(credit_col, 2)
        })
        total_debit += debit_col
        total_credit += credit_col
    
    return jsonify({
        'success': True, 'data': result,
        'totals': {
            'debit': round(total_debit, 2),
            'credit': round(total_credit, 2),
            'balanced': abs(total_debit - total_credit) < 0.01
        }
    })


@fin_bp.route('/balance-sheet', methods=['GET'])
def balance_sheet():
    as_of = request.args.get('as_of')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, None, as_of)
    
    assets, liabilities, equity = [], [], []
    
    for a in accounts:
        if a['level'] == 'L1':
            continue
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        if td == 0 and tc == 0:
            continue
        
        balance = (td - tc) if a['nature'] == 'D' else (tc - td)
        if abs(balance) < 0.01:
            continue
        
        row = {'code': a['code'], 'name_ar': a['name_ar'], 'level': a['level'], 'balance': round(balance, 2)}
        
        if a['code'].startswith('1'):
            assets.append(row)
        elif a['code'].startswith('2'):
            liabilities.append(row)
        elif a['code'].startswith('8'):
            equity.append(row)
    
    ta = sum(r['balance'] for r in assets)
    tl = sum(r['balance'] for r in liabilities)
    te = sum(r['balance'] for r in equity)
    
    # تصنيف المخزون
    inventory_breakdown = {}
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                COALESCE(i.operating_type, 'OPERATING') as operating_type,
                COUNT(DISTINCT i.id) as item_count,
                COALESCE(SUM(sb.total_value), 0) as total_value
            FROM items i
            LEFT JOIN stock_balances sb ON i.id = sb.item_id
            GROUP BY i.operating_type
        """).fetchall()
        
        for r in rows:
            inventory_breakdown[r['operating_type']] = {
                'item_count': r['item_count'],
                'value': float(r['total_value'] or 0)
            }
    
    return jsonify({
        'success': True,
        'data': {
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'inventory_breakdown': inventory_breakdown,
            'totals': {
                'assets': round(ta, 2),
                'liabilities': round(tl, 2),
                'equity': round(te, 2),
                'liab_plus_equity': round(tl + te, 2),
                'balanced': abs(ta - (tl + te)) < 0.01
            }
        }
    })


@fin_bp.route('/income-statement', methods=['GET'])
def income_statement():
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)
    
    revenue, cogs, expenses, other_income, finance_costs, taxes = [], [], [], [], [], []
    
    for a in accounts:
        if a['level'] == 'L1':
            continue
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        if td == 0 and tc == 0:
            continue
        
        code = a['code']
        
        if code.startswith('4'):
            balance = tc - td
            if abs(balance) < 0.01: continue
            row = {'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)}
            (other_income if code.startswith('42') else revenue).append(row)
        elif code.startswith('3'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            cogs.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        elif code.startswith('5'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            expenses.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        elif code.startswith('6'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            finance_costs.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        elif code.startswith('7'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            taxes.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
    
    tr = sum(r['amount'] for r in revenue)
    toi = sum(r['amount'] for r in other_income)
    tcg = sum(r['amount'] for r in cogs)
    texp = sum(r['amount'] for r in expenses)
    tf = sum(r['amount'] for r in finance_costs)
    ttx = sum(r['amount'] for r in taxes)
    gp = tr - tcg
    op = gp - texp
    pbt = op + toi - tf
    np = pbt - ttx
    
    return jsonify({
        'success': True,
        'data': {
            'revenue': revenue, 'other_income': other_income, 'cogs': cogs,
            'expenses': expenses, 'finance_costs': finance_costs, 'taxes': taxes,
            'totals': {
                'total_revenue': round(tr, 2), 'total_other_income': round(toi, 2),
                'total_cogs': round(tcg, 2), 'total_expenses': round(texp, 2),
                'total_finance': round(tf, 2), 'total_taxes': round(ttx, 2),
                'gross_profit': round(gp, 2), 'operating_profit': round(op, 2),
                'profit_before_tax': round(pbt, 2), 'net_profit': round(np, 2)
            }
        }
    })


@fin_bp.route('/inventory-by-operating-type', methods=['GET'])
def inventory_by_operating_type():
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                COALESCE(i.operating_type, 'OPERATING') as operating_type,
                COUNT(DISTINCT i.id) as item_count,
                COALESCE(SUM(sb.quantity), 0) as total_qty,
                COALESCE(SUM(sb.total_value), 0) as total_value
            FROM items i
            LEFT JOIN stock_balances sb ON i.id = sb.item_id
            GROUP BY i.operating_type
        """).fetchall()
    
    labels = {
        'OPERATING': 'مخزون تشغيلي (COGS)',
        'NON_OPERATING': 'مخزون غير تشغيلي (OPEX)',
        'CAPITAL': 'قطع غيار رأسمالية (أصول)'
    }
    
    result = []
    total = 0
    for r in rows:
        val = float(r['total_value'] or 0)
        total += val
        result.append({
            'operating_type': r['operating_type'],
            'label_ar': labels.get(r['operating_type'], r['operating_type']),
            'item_count': r['item_count'],
            'total_qty': float(r['total_qty'] or 0),
            'total_value': val
        })
    
    return jsonify({'success': True, 'data': result, 'total_value': total})


@fin_bp.route('/account-ledger/<code>', methods=['GET'])
def account_ledger(code):
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    
    cond = ['jel.account_code = ?']
    vals = [code]
    if df:
        cond.append('je.entry_date >= ?'); vals.append(df)
    if dt:
        cond.append('je.entry_date <= ?'); vals.append(dt)
    where = ' AND '.join(cond)
    
    with db.get_connection() as conn:
        acc = conn.execute("SELECT * FROM accounts WHERE code=?", (code,)).fetchone()
        if not acc:
            return jsonify({'success': False, 'message': 'الحساب غير موجود'}), 404
        
        rows = conn.execute(f"""
            SELECT je.entry_date, je.entry_no, je.description, je.reference_no,
                   jel.debit_amount, jel.credit_amount
            FROM journal_entry_lines jel
            JOIN journal_entries je ON jel.journal_entry_id = je.id
            WHERE {where}
            ORDER BY je.entry_date, je.id
        """, vals).fetchall()
    
    running = 0
    result = []
    for r in rows:
        running += float(r['debit_amount'] or 0) - float(r['credit_amount'] or 0)
        result.append({
            'entry_date': r['entry_date'], 'entry_no': r['entry_no'],
            'description': r['description'], 'reference_no': r['reference_no'],
            'debit': float(r['debit_amount'] or 0), 'credit': float(r['credit_amount'] or 0),
            'balance': round(running, 2)
        })
    
    return jsonify({'success': True, 'data': {'account': dict(acc), 'transactions': result}})


@fin_bp.route('/aging/ar', methods=['GET'])
def aging_ar():
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT si.invoice_no, si.invoice_date, si.total_amount, si.status,
                   c.name_ar as customer_name,
                   CAST(julianday('now') - julianday(si.invoice_date) AS INTEGER) as days_old
            FROM sales_invoices si
            LEFT JOIN customers c ON si.customer_id = c.id
            WHERE si.status = 'POSTED'
            ORDER BY si.invoice_date
        """).fetchall()
    
    result = []
    buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
    
    for r in rows:
        d = r['days_old']
        bucket = '0-30' if d <= 30 else ('31-60' if d <= 60 else ('61-90' if d <= 90 else '90+'))
        buckets[bucket] += float(r['total_amount'])
        result.append({
            'invoice_no': r['invoice_no'], 'invoice_date': r['invoice_date'],
            'customer_name': r['customer_name'], 'amount': float(r['total_amount']),
            'days_old': d, 'bucket': bucket
        })
    
    return jsonify({'success': True, 'data': result, 'buckets': buckets})


@fin_bp.route('/cash-flow', methods=['GET'])
def cash_flow():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if not from_date or not to_date:
        from datetime import date
        today = date.today().isoformat()
        from_date = from_date or today
        to_date = to_date or today
    try:
        with db.get_connection() as conn:
            def get_bal(prefix, limit, is_lt=False):
                if not limit:
                    return 0.0
                op = '<' if is_lt else '<='
                q = f"""SELECT COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                        FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                        WHERE je.status = 'POSTED' AND je.entry_date {op} ? AND jl.account_code LIKE ?"""
                res = conn.execute(q, (limit, prefix + '%')).fetchone()
                return float(res['bal']) if res else 0.0

            def get_change(prefix):
                return get_bal(prefix, to_date) - get_bal(prefix, from_date, True)

            rev_bal = -(get_change('4'))
            cogs_bal = get_change('3')
            exp_bal = get_change('5')
            net_profit = rev_bal - abs(cogs_bal) - abs(exp_bal)
            depreciation = get_change('63')

            inv = get_change('124')
            ar = get_change('123')
            ap = get_change('221')
            wc = -inv - ar + ap
            net_operating = net_profit + depreciation + wc

            fa = get_change('111')
            net_investing = -fa
            fa_purchased = fa if fa > 0 else 0
            fa_sold = -fa if fa < 0 else 0

            cap = get_change('8')
            loans = get_change('211') + get_change('225')
            net_financing = cap + loans

            cash_prefixes = ['121']
            start_cash = sum(get_bal(p, from_date, True) for p in cash_prefixes)
            end_cash = sum(get_bal(p, to_date) for p in cash_prefixes)
            net_change = end_cash - start_cash

            return jsonify({
                'success': True,
                'data': {
                    'start_balance': start_cash,
                    'end_balance': end_cash,
                    'net_change': net_change,
                    'net_profit': net_profit,
                    'depreciation': depreciation,
                    'operating': {'total': net_operating},
                    'investing': {
                        'items': [{'name': 'أصول ثابتة', 'amount': -fa}],
                        'total': net_investing
                    },
                    'financing': {
                        'items': [{'name': 'رأس المال', 'amount': cap}, {'name': 'قروض', 'amount': loans}],
                        'total': net_financing
                    },
                    'working_capital': {
                        'inventory_change': inv,
                        'receivables_change': ar,
                        'payables_change': ap,
                        'total': wc
                    },
                    'investing_activities': {
                        'fixed_assets_purchased': fa_purchased,
                        'fixed_assets_sold': fa_sold,
                        'total': net_investing
                    },
                    'financing_activities': {
                        'capital_raised': cap,
                        'loans': loans,
                        'total': net_financing
                    }
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@fin_bp.route('/aging/ap', methods=['GET'])
def aging_ap():
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT pi.invoice_no, pi.invoice_date, pi.total_amount, pi.status,
                   s.name_ar as supplier_name,
                   CAST(julianday('now') - julianday(pi.invoice_date) AS INTEGER) as days_old
            FROM purchase_invoices pi
            LEFT JOIN suppliers s ON pi.supplier_id = s.id
            WHERE pi.status = 'POSTED'
            ORDER BY pi.invoice_date
        """).fetchall()
    
    result = []
    buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
    
    for r in rows:
        d = r['days_old']
        bucket = '0-30' if d <= 30 else ('31-60' if d <= 60 else ('61-90' if d <= 90 else '90+'))
        buckets[bucket] += float(r['total_amount'])
        result.append({
            'invoice_no': r['invoice_no'], 'invoice_date': r['invoice_date'],
            'supplier_name': r['supplier_name'], 'amount': float(r['total_amount']),
            'days_old': d, 'bucket': bucket
        })
    
    return jsonify({'success': True, 'data': result, 'buckets': buckets})