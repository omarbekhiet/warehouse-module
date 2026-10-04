from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

fin_bp = Blueprint('financial_reports', __name__)


def _get_balance_per_account(conn, date_from=None, date_to=None):
    """حساب رصيد كل حساب (مدين - دائن) خلال فترة."""
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
    """ميزان المراجعة."""
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)
    
    result = []
    total_debit = 0
    total_credit = 0
    
    for a in accounts:
        # حساب الرصيد حسب طبيعة الحساب
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        
        if td == 0 and tc == 0:
            continue
        
        # للأصول والمصروفات: طبيعة مدين → الرصيد = debit - credit
        # للخصوم والإيرادات وحقوق الملكية: طبيعة دائن → الرصيد = credit - debit
        if a['nature'] in ('D',):
            balance = td - tc
            debit_col = balance if balance > 0 else 0
            credit_col = abs(balance) if balance < 0 else 0
        elif a['nature'] in ('C', 'CC'):
            balance = tc - td
            credit_col = balance if balance > 0 else 0
            debit_col = abs(balance) if balance < 0 else 0
        else:
            balance = td - tc
            debit_col = balance if balance > 0 else 0
            credit_col = abs(balance) if balance < 0 else 0
        
        result.append({
            'code': a['code'],
            'name_ar': a['name_ar'],
            'level': a['level'],
            'nature': a['nature'],
            'total_debit': td,
            'total_credit': tc,
            'debit_balance': round(debit_col, 2),
            'credit_balance': round(credit_col, 2)
        })
        
        total_debit += debit_col
        total_credit += credit_col
    
    return jsonify({
        'success': True,
        'data': result,
        'totals': {
            'debit': round(total_debit, 2),
            'credit': round(total_credit, 2),
            'balanced': abs(total_debit - total_credit) < 0.01
        }
    })


@fin_bp.route('/balance-sheet', methods=['GET'])
def balance_sheet():
    """الميزانية العمومية."""
    as_of = request.args.get('as_of')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, None, as_of)
    
    assets = []
    liabilities = []
    equity = []
    
    for a in accounts:
        if a['level'] == 'L1':
            continue  # تخطي المستوى الرئيسي
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        if td == 0 and tc == 0:
            continue
        
        if a['nature'] == 'D':
            balance = td - tc
        else:
            balance = tc - td
        
        if abs(balance) < 0.01:
            continue
        
        row = {
            'code': a['code'],
            'name_ar': a['name_ar'],
            'level': a['level'],
            'balance': round(balance, 2)
        }
        
        if a['code'].startswith('1'):
            assets.append(row)
        elif a['code'].startswith('2'):
            liabilities.append(row)
        elif a['code'].startswith('8'):
            equity.append(row)
    
    total_assets = sum(r['balance'] for r in assets)
    total_liab = sum(r['balance'] for r in liabilities)
    total_equity = sum(r['balance'] for r in equity)
    
    return jsonify({
        'success': True,
        'data': {
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'totals': {
                'assets': round(total_assets, 2),
                'liabilities': round(total_liab, 2),
                'equity': round(total_equity, 2),
                'liab_plus_equity': round(total_liab + total_equity, 2),
                'balanced': abs(total_assets - (total_liab + total_equity)) < 0.01
            }
        }
    })


@fin_bp.route('/income-statement', methods=['GET'])
def income_statement():
    """قائمة الدخل."""
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)
    
    revenue = []
    cogs = []
    expenses = []
    other_income = []
    finance_costs = []
    taxes = []
    
    for a in accounts:
        if a['level'] == 'L1':
            continue
        td = float(a['total_debit'] or 0)
        tc = float(a['total_credit'] or 0)
        if td == 0 and tc == 0:
            continue
        
        code = a['code']
        
        # Revenue 4xxx: credit - debit
        if code.startswith('4'):
            balance = tc - td
            if abs(balance) < 0.01: continue
            row = {'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)}
            if code.startswith('42'):
                other_income.append(row)
            else:
                revenue.append(row)
        
        # COGS 3xxx: debit - credit
        elif code.startswith('3'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            cogs.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        
        # Expenses 5xxx
        elif code.startswith('5'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            expenses.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        
        # Finance 6xxx
        elif code.startswith('6'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            finance_costs.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
        
        # Tax 7xxx
        elif code.startswith('7'):
            balance = td - tc
            if abs(balance) < 0.01: continue
            taxes.append({'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)})
    
    total_revenue = sum(r['amount'] for r in revenue)
    total_other_income = sum(r['amount'] for r in other_income)
    total_cogs = sum(r['amount'] for r in cogs)
    total_expenses = sum(r['amount'] for r in expenses)
    total_finance = sum(r['amount'] for r in finance_costs)
    total_taxes = sum(r['amount'] for r in taxes)
    
    gross_profit = total_revenue - total_cogs
    operating_profit = gross_profit - total_expenses
    profit_before_tax = operating_profit + total_other_income - total_finance
    net_profit = profit_before_tax - total_taxes
    
    return jsonify({
        'success': True,
        'data': {
            'revenue': revenue,
            'other_income': other_income,
            'cogs': cogs,
            'expenses': expenses,
            'finance_costs': finance_costs,
            'taxes': taxes,
            'totals': {
                'total_revenue': round(total_revenue, 2),
                'total_other_income': round(total_other_income, 2),
                'total_cogs': round(total_cogs, 2),
                'total_expenses': round(total_expenses, 2),
                'total_finance': round(total_finance, 2),
                'total_taxes': round(total_taxes, 2),
                'gross_profit': round(gross_profit, 2),
                'operating_profit': round(operating_profit, 2),
                'profit_before_tax': round(profit_before_tax, 2),
                'net_profit': round(net_profit, 2)
            }
        }
    })


@fin_bp.route('/account-ledger/<code>', methods=['GET'])
def account_ledger(code):
    """دفتر الأستاذ لحساب معين."""
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
    
    # حساب الرصيد التراكمي
    running = 0
    result = []
    for r in rows:
        running += float(r['debit_amount'] or 0) - float(r['credit_amount'] or 0)
        result.append({
            'entry_date': r['entry_date'],
            'entry_no': r['entry_no'],
            'description': r['description'],
            'reference_no': r['reference_no'],
            'debit': float(r['debit_amount'] or 0),
            'credit': float(r['credit_amount'] or 0),
            'balance': round(running, 2)
        })
    
    return jsonify({
        'success': True,
        'data': {
            'account': dict(acc),
            'transactions': result
        }
    })


@fin_bp.route('/aging/ar', methods=['GET'])
def aging_ar():
    """أعمار الذمم المدينة (AR) - من فواتير البيع."""
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                si.invoice_no, si.invoice_date, si.total_amount, si.status,
                c.name_ar as customer_name, c.id as customer_id,
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
        if d <= 30: buckets['0-30'] += float(r['total_amount'])
        elif d <= 60: buckets['31-60'] += float(r['total_amount'])
        elif d <= 90: buckets['61-90'] += float(r['total_amount'])
        else: buckets['90+'] += float(r['total_amount'])
        
        result.append({
            'invoice_no': r['invoice_no'],
            'invoice_date': r['invoice_date'],
            'customer_name': r['customer_name'],
            'amount': float(r['total_amount']),
            'days_old': d,
            'bucket': '0-30' if d <= 30 else ('31-60' if d <= 60 else ('61-90' if d <= 90 else '90+'))
        })
    
    return jsonify({'success': True, 'data': result, 'buckets': buckets})


@fin_bp.route('/aging/ap', methods=['GET'])
def aging_ap():
    """أعمار الذمم الدائنة (AP) - من فواتير الشراء."""
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                pi.invoice_no, pi.invoice_date, pi.total_amount, pi.status,
                s.name_ar as supplier_name, s.id as supplier_id,
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
        if d <= 30: buckets['0-30'] += float(r['total_amount'])
        elif d <= 60: buckets['31-60'] += float(r['total_amount'])
        elif d <= 90: buckets['61-90'] += float(r['total_amount'])
        else: buckets['90+'] += float(r['total_amount'])
        
        result.append({
            'invoice_no': r['invoice_no'],
            'invoice_date': r['invoice_date'],
            'supplier_name': r['supplier_name'],
            'amount': float(r['total_amount']),
            'days_old': d,
            'bucket': '0-30' if d <= 30 else ('31-60' if d <= 60 else ('61-90' if d <= 90 else '90+'))
        })
    
    return jsonify({'success': True, 'data': result, 'buckets': buckets})
