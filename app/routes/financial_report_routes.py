from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

fin_bp = Blueprint('financial_reports', __name__)


def _get_balance_per_account(conn, date_from=None, date_to=None):
    """يرجّع لكل حساب: opening_debit, opening_credit, period_debit, period_credit"""
    opening_cond, opening_vals = [], []
    if date_from:
        opening_cond.append('je.entry_date < ?')
        opening_vals.append(date_from)

    period_cond, period_vals = [], []
    if date_from:
        period_cond.append('je.entry_date >= ?')
        period_vals.append(date_from)
    if date_to:
        period_cond.append('je.entry_date <= ?')
        period_vals.append(date_to)

    opening_where = (' AND '.join(opening_cond)) if opening_cond else '1=0'
    period_where = (' AND '.join(period_cond)) if period_cond else '1=1'

    sql = f"""
        SELECT
            a.code, a.name_ar, a.level, a.nature, a.financial_statement,
            a.bs_group, a.pl_group, a.is_leaf,
            a.ifrs18_category, a.ifrs18_subcategory, a.ifrs18_statement,
            COALESCE(SUM(CASE WHEN {opening_where} THEN jel.debit_amount ELSE 0 END), 0) AS opening_debit,
            COALESCE(SUM(CASE WHEN {opening_where} THEN jel.credit_amount ELSE 0 END), 0) AS opening_credit,
            COALESCE(SUM(CASE WHEN {period_where} THEN jel.debit_amount ELSE 0 END), 0) AS period_debit,
            COALESCE(SUM(CASE WHEN {period_where} THEN jel.credit_amount ELSE 0 END), 0) AS period_credit
        FROM accounts a
        LEFT JOIN journal_entry_lines jel ON jel.account_code = a.code
        LEFT JOIN journal_entries je ON jel.journal_entry_id = je.id
        GROUP BY a.code
        ORDER BY a.code
    """

    # ترتيب القيم الصحيح:
    # opening_where تظهر مرتين في الـ SQL → opening_vals مرتين
    # period_where تظهر مرتين في الـ SQL → period_vals مرتين
    all_vals = opening_vals + opening_vals + period_vals + period_vals

    rows = conn.execute(sql, all_vals).fetchall()
    return [dict(r) for r in rows]


@fin_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    as_of = request.args.get('as_of')

    # منطق دمج as_of:
    # - لو as_of موجود + مفيش df/dt → الرصيد التراكمي لحد as_of
    # - لو as_of موجود + df/dt موجودين → الحركة بين df/dt + رصيد آخر المدة لحد as_of
    # - لو as_of مش موجود → السلوك القديم (df/dt)
    if as_of:
        # لو مفيش dt، استخدم as_of كنهاية للحركة
        if not dt:
            dt = as_of
        # لو مفيش df، ابدأ من تاريخ قديم جداً عشان نجمع كل الحركات
        if not df:
            df = '1900-01-01'

    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)

    result = []
    tot = {
        'opening_debit': 0, 'opening_credit': 0,
        'period_debit': 0, 'period_credit': 0,
        'closing_debit': 0, 'closing_credit': 0
    }

    for a in accounts:
        od = float(a['opening_debit'] or 0)
        oc = float(a['opening_credit'] or 0)
        pd = float(a['period_debit'] or 0)
        pc = float(a['period_credit'] or 0)

        if od == 0 and oc == 0 and pd == 0 and pc == 0:
            continue

        is_debit_nature = (a['nature'] == 'D')

        # ============================================================
        # حساب صافي الرصيد حسب طبيعة الحساب
        # ============================================================
        # للحسابات المدينة بطبيعتها (D): الرصيد = مدين - دائن
        # للحسابات الدائنة بطبيعتها (C): الرصيد = دائن - مدين
        # ============================================================
        opening_net = (od - oc) if is_debit_nature else (oc - od)
        period_net = (pd - pc) if is_debit_nature else (pc - pd)
        closing_net = opening_net + period_net

        # توزيع الأرصدة على الأعمدة حسب الطبيعة والإشارة
        if is_debit_nature:
            # أصول / مصروفات → مدين
            opening_debit_col = opening_net if opening_net > 0 else 0
            opening_credit_col = abs(opening_net) if opening_net < 0 else 0
            closing_debit_col = closing_net if closing_net > 0 else 0
            closing_credit_col = abs(closing_net) if closing_net < 0 else 0
        else:
            # خصوم / إيرادات / حقوق ملكية → دائن
            opening_credit_col = opening_net if opening_net > 0 else 0
            opening_debit_col = abs(opening_net) if opening_net < 0 else 0
            closing_credit_col = closing_net if closing_net > 0 else 0
            closing_debit_col = abs(closing_net) if closing_net < 0 else 0

        result.append({
            'code': a['code'], 'name_ar': a['name_ar'], 'level': a['level'],
            'nature': a['nature'],
            'ifrs18_category': a.get('ifrs18_category') or '',
            'ifrs18_subcategory': a.get('ifrs18_subcategory') or '',
            'ifrs18_statement': a.get('ifrs18_statement') or '',
            'financial_statement': a.get('financial_statement') or '',
            'opening_debit': round(opening_debit_col, 2),
            'opening_credit': round(opening_credit_col, 2),
            'period_debit': round(pd, 2),
            'period_credit': round(pc, 2),
            'closing_debit': round(closing_debit_col, 2),
            'closing_credit': round(closing_credit_col, 2),
        })

        tot['opening_debit'] += opening_debit_col
        tot['opening_credit'] += opening_credit_col
        tot['period_debit'] += pd
        tot['period_credit'] += pc
        tot['closing_debit'] += closing_debit_col
        tot['closing_credit'] += closing_credit_col

    return jsonify({
        'success': True,
        'data': result,
        'totals': {k: round(v, 2) for k, v in tot.items()}
    })

@fin_bp.route('/balance-sheet', methods=['GET'])
def balance_sheet():
    """
    الميزانية العمومية حسب IFRS 18 + IAS 1
    
    التصنيف:
    - 1xxx → الأصول (Assets)
    - 2xxx → الالتزامات (Liabilities)
    - 3xxx → حقوق الملكية (Equity)
    
    ملاحظة: نستخدم الأرصدة التراكمية (opening + period) لحد as_of
    """
    as_of = request.args.get('as_of')
    
    with db.get_connection() as conn:
        # ⚠️ نمرر date_from = None عشان opening = 0
        # و date_to = as_of عشان period = كل الحركات لحد as_of
        accounts = _get_balance_per_account(conn, None, as_of)
    
    assets, liabilities, equity = [], [], []
    
    for a in accounts:
        if a['level'] == 'L1':
            continue
        
        # ⚠️ الرصيد التراكمي = opening + period
        od = float(a['opening_debit'] or 0)
        oc = float(a['opening_credit'] or 0)
        pd = float(a['period_debit'] or 0)
        pc = float(a['period_credit'] or 0)
        
        # إجمالي الحركة (التراكمي لحد as_of)
        total_debit = od + pd
        total_credit = oc + pc
        
        if total_debit == 0 and total_credit == 0:
            continue
        
        code = a['code']
        nature = a.get('nature', 'D')
        stmt = (a.get('ifrs18_statement') or '').upper()
        cat = (a.get('ifrs18_category') or '').upper()
        sub = (a.get('ifrs18_subcategory') or '').upper()
        
        # ⚠️ تصنيف الحسابات:
        # - الأصول: 1xxx (BS) — ما عدا الإهلاك المتراكم (112x) اللي بيخصم
        # - الالتزامات: 2xxx (BS)
        # - حقوق الملكية: 3xxx (BS)
        
        # تخطي حسابات قائمة الدخل (IS) والضرائب (TAX)
        if code.startswith(('4', '5', '6', '7')):
            continue
        
        # حساب الرصيد حسب الطبيعة
        if nature == 'D':
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit
        
        if abs(balance) < 0.01:
            continue
        
        row = {
            'code': code,
            'name_ar': a['name_ar'],
            'level': a['level'],
            'nature': nature,
            'ifrs18_category': cat,
            'ifrs18_subcategory': sub,
            'balance': round(balance, 2)
        }
        
        # تصنيف حسب الكود
        if code.startswith('1'):
            # الإهلاك المتراكم والمخصصات → تخصم من الأصول (تظهر بالسالب)
            if code.startswith('112') or code.startswith('113'):
                row['balance'] = -abs(row['balance'])  # نخليها سالبة دايماً
            assets.append(row)
        elif code.startswith('2'):
            liabilities.append(row)
        elif code.startswith('3'):
            equity.append(row)
    
    ta = sum(r['balance'] for r in assets)
    tl = sum(r['balance'] for r in liabilities)
    te = sum(r['balance'] for r in equity)
    
    # تصنيف المخزون حسب نوع التشغيل
    inventory_breakdown = {}
    try:
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
    except Exception as e:
        print(f"Warning: {e}")
    
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
    """
    قائمة الدخل حسب IFRS 18
    
    الفئات:
    - OPERATING / REVENUE      → الإيرادات
    - OPERATING / COGS         → تكلفة المبيعات
    - OPERATING / SELLING      → مصروفات بيعية
    - OPERATING / ADMIN        → مصروفات إدارية
    - OPERATING / DEPRECIATION → إهلاك
    - INVESTING                → إيرادات/خسائر استثمارية
    - FINANCING                → تكاليف تمويل
    - TAX                      → ضرائب
    """
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    as_of = request.args.get('as_of')

    if as_of and not dt:
        dt = as_of

    with db.get_connection() as conn:
        accounts = _get_balance_per_account(conn, df, dt)

    # الفئات حسب IFRS 18
    revenue = []          # OPERATING / REVENUE
    cogs = []             # OPERATING / COGS
    selling = []          # OPERATING / SELLING
    admin = []            # OPERATING / ADMIN
    depreciation = []     # OPERATING / DEPRECIATION
    other_operating = []  # OPERATING / أخرى
    investing_income = [] # INVESTING / إيرادات
    investing_loss = []   # INVESTING / خسائر
    finance_costs = []    # FINANCING
    taxes = []            # TAX

    for a in accounts:
        if a['level'] == 'L1':
            continue

        td = float(a['period_debit'] or 0)
        tc = float(a['period_credit'] or 0)
        if td == 0 and tc == 0:
            continue

        code = a['code']
        cat = (a.get('ifrs18_category') or '').upper()
        sub = (a.get('ifrs18_subcategory') or '').upper()
        stmt = (a.get('ifrs18_statement') or '').upper()
        nature = a.get('nature', 'D')

        # ⚠️ نستثني حسابات الميزانية (BS) — العملاء، الموردين، المخزون
        if stmt == 'BS' and not code.startswith(('4', '5', '6', '7')):
            continue

        # صافي الرصيد حسب طبيعة الحساب
        if nature == 'D':
            balance = td - tc
        else:
            balance = tc - td

        if abs(balance) < 0.01:
            continue

        row = {
            'code': code,
            'name_ar': a['name_ar'],
            'amount': round(balance, 2)
        }

        # ===== التصنيف حسب IFRS 18 =====
        if cat == 'OPERATING':
            if sub == 'REVENUE':
                revenue.append(row)
            elif sub == 'COGS':
                cogs.append(row)
            elif sub == 'SELLING':
                selling.append(row)
            elif sub == 'ADMIN':
                admin.append(row)
            elif sub == 'DEPRECIATION':
                depreciation.append(row)
            else:
                # fallback حسب الكود
                if code.startswith('4'):
                    revenue.append(row)
                elif code.startswith('6'):
                    cogs.append(row)
                elif code.startswith('51'):
                    selling.append(row)
                elif code.startswith('52'):
                    admin.append(row)
                elif code.startswith('53'):
                    depreciation.append(row)
                else:
                    other_operating.append(row)

        elif cat == 'INVESTING':
            # الإيرادات موجبة، الخسائر سالبة
            if sub in ('GAIN_ON_SALE', 'INTEREST_INCOME', 'INVESTMENT_INCOME',
                       'RENTAL_INCOME', 'ROYALTY_INCOME', 'FX_GAIN'):
                investing_income.append(row)
            elif sub in ('LOSS_ON_SALE', 'FX_LOSS'):
                # نخليها بالسالب
                row['amount'] = -abs(row['amount'])
                investing_loss.append(row)
            else:
                # fallback حسب الكود
                if code.startswith('72'):
                    investing_income.append(row)
                else:
                    investing_loss.append(row)

        elif cat == 'FINANCING':
            # تكاليف التمويل (مصروفات)
            finance_costs.append(row)

        elif cat == 'TAX':
            taxes.append(row)

        else:
            # fallback حسب الكود (للحسابات القديمة)
            if code.startswith('4'):
                revenue.append(row)
            elif code.startswith('3'):
                cogs.append(row)
            elif code.startswith('5'):
                admin.append(row)
            elif code.startswith('6'):
                finance_costs.append(row)
            elif code.startswith('7'):
                taxes.append(row)

    # ===== الحسابات =====
    tr = sum(r['amount'] for r in revenue)
    tcg = sum(r['amount'] for r in cogs)
    tselling = sum(r['amount'] for r in selling)
    tadmin = sum(r['amount'] for r in admin)
    tdepr = sum(r['amount'] for r in depreciation)
    tother_op = sum(r['amount'] for r in other_operating)
    t_opex = tselling + tadmin + tdepr + tother_op

    t_inv_income = sum(r['amount'] for r in investing_income)
    t_inv_loss = sum(r['amount'] for r in investing_loss)  # بالسالب
    t_investing = t_inv_income + t_inv_loss

    t_finance = sum(r['amount'] for r in finance_costs)
    t_tax = sum(r['amount'] for r in taxes)

    # ===== المجاميع الإلزامية حسب IFRS 18 =====
    gross_profit = tr - tcg                              # إجمالي الربح
    operating_profit = gross_profit - t_opex             # الربح التشغيلي
    ebit = operating_profit + t_investing                # EBIT
    profit_before_tax = ebit - t_finance                 # الربح قبل الضريبة
    net_profit = profit_before_tax - t_tax               # صافي الربح

    return jsonify({
        'success': True,
        'data': {
            # الفئات حسب IFRS 18
            'revenue': revenue,
            'cogs': cogs,
            'selling_expenses': selling,
            'admin_expenses': admin,
            'depreciation_expenses': depreciation,
            'other_operating': other_operating,
            'investing_income': investing_income,
            'investing_loss': investing_loss,
            'finance_costs': finance_costs,
            'taxes': taxes,

            # المجاميع الفرعية
            'totals': {
                'total_revenue': round(tr, 2),
                'total_cogs': round(tcg, 2),
                'total_selling': round(tselling, 2),
                'total_admin': round(tadmin, 2),
                'total_depreciation': round(tdepr, 2),
                'total_other_operating': round(tother_op, 2),
                'total_opex': round(t_opex, 2),
                'total_investing_income': round(t_inv_income, 2),
                'total_investing_loss': round(t_inv_loss, 2),
                'total_investing': round(t_investing, 2),
                'total_finance': round(t_finance, 2),
                'total_taxes': round(t_tax, 2),

                # المجاميع الإلزامية حسب IFRS 18
                'gross_profit': round(gross_profit, 2),
                'operating_profit': round(operating_profit, 2),
                'ebit': round(ebit, 2),
                'profit_before_tax': round(profit_before_tax, 2),
                'net_profit': round(net_profit, 2),
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

# ============================================================
# شاشة إدارة التصنيفات IFRS 18
# ============================================================
@fin_bp.route('/ifrs18/categories', methods=['GET'])
def ifrs18_categories():
    """يرجّع قائمة التصنيفات المتاحة"""
    return jsonify({
        'success': True,
        'categories': [
            {'value': 'OPERATING', 'label_ar': 'تشغيلي', 'icon': 'briefcase', 'color': '#2563eb'},
            {'value': 'INVESTING', 'label_ar': 'استثماري', 'icon': 'bank', 'color': '#d97706'},
            {'value': 'FINANCING', 'label_ar': 'تمويلي', 'icon': 'cash-stack', 'color': '#7c3aed'},
            {'value': 'TAX', 'label_ar': 'ضريبي', 'icon': 'percent', 'color': '#475569'},
            {'value': 'OCI', 'label_ar': 'الدخل الشامل الآخر', 'icon': 'arrow-repeat', 'color': '#0891b2'},
            {'value': 'DISCONTINUED', 'label_ar': 'عمليات متوقفة', 'icon': 'x-circle', 'color': '#dc2626'},
        ],
        'subcategories': {
            'OPERATING': [
                {'value': 'REVENUE', 'label_ar': 'إيرادات'},
                {'value': 'COGS', 'label_ar': 'تكلفة المبيعات'},
                {'value': 'SELLING', 'label_ar': 'مصروفات بيعية'},
                {'value': 'ADMIN', 'label_ar': 'مصروفات إدارية'},
                {'value': 'DEPRECIATION', 'label_ar': 'إهلاك وإطفاء'},
                {'value': 'OTHER_OPEX', 'label_ar': 'مصروفات أخرى'},
                {'value': 'TRADE_RECEIVABLE', 'label_ar': 'عملاء'},
                {'value': 'TRADE_PAYABLE', 'label_ar': 'موردين'},
                {'value': 'INVENTORY', 'label_ar': 'مخزون'},
            ],
            'INVESTING': [
                {'value': 'INTEREST_INCOME', 'label_ar': 'فوائد دائنة'},
                {'value': 'INVESTMENT_INCOME', 'label_ar': 'إيرادات استثمارات'},
                {'value': 'RENTAL_INCOME', 'label_ar': 'إيرادات إيجارات'},
                {'value': 'ROYALTY_INCOME', 'label_ar': 'إيرادات حقوق'},
                {'value': 'GAIN_ON_SALE', 'label_ar': 'أرباح بيع أصول'},
                {'value': 'LOSS_ON_SALE', 'label_ar': 'خسائر بيع أصول'},
                {'value': 'FX_GAIN', 'label_ar': 'فروق عملة دائنة'},
                {'value': 'FX_LOSS', 'label_ar': 'فروق عملة مدينة'},
            ],
            'FINANCING': [
                {'value': 'INTEREST_EXPENSE', 'label_ar': 'فوائد مدينة'},
                {'value': 'FX_LOSS', 'label_ar': 'فروق عملة مدينة'},
            ],
            'TAX': [
                {'value': 'CURRENT_TAX', 'label_ar': 'ضريبة حالية'},
                {'value': 'DEFERRED_TAX', 'label_ar': 'ضريبة مؤجلة'},
                {'value': 'STAMP_TAX', 'label_ar': 'ضريبة دمغة'},
                {'value': 'TAX_PROVISION', 'label_ar': 'مخصص ضرائب'},
            ],
            'OCI': [
                {'value': 'REVALUATION', 'label_ar': 'إعادة تقييم'},
                {'value': 'ACTUARIAL', 'label_ar': 'أرباح/خسائر اكتوارية'},
            ],
        },
        'statements': [
            {'value': 'IS', 'label_ar': 'قائمة الدخل'},
            {'value': 'BS', 'label_ar': 'الميزانية العمومية'},
            {'value': 'OCI', 'label_ar': 'الدخل الشامل الآخر'},
            {'value': 'TAX', 'label_ar': 'الضرائب'},
        ]
    })


@fin_bp.route('/ifrs18/accounts', methods=['GET'])
def ifrs18_accounts():
    """يرجّع الحسابات مع تصنيفاتها"""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    statement = request.args.get('statement', '').strip()
    only_leaf = request.args.get('only_leaf', '1') == '1'
    
    where_parts = []
    params = []
    
    if only_leaf:
        where_parts.append("is_leaf = 1")
    
    if search:
        where_parts.append("(code LIKE ? OR name_ar LIKE ?)")
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category:
        where_parts.append("ifrs18_category = ?")
        params.append(category)
    
    if statement:
        where_parts.append("ifrs18_statement = ?")
        params.append(statement)
    
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    
    sql = f"""
        SELECT 
            code, name_ar, level, nature,
            financial_statement, is_leaf,
            ifrs18_category, ifrs18_subcategory, ifrs18_statement
        FROM accounts
        {where_sql}
        ORDER BY code
        LIMIT 500
    """
    
    rows = db.query(sql, tuple(params))
    
    return jsonify({
        'success': True,
        'data': json_safe(rows),
        'count': len(rows)
    })


@fin_bp.route('/ifrs18/stats', methods=['GET'])
def ifrs18_stats():
    """إحصائيات التصنيفات"""
    stats = {
        'categories': {},
        'subcategories': {},
        'statements': {},
        'total': 0,
        'unclassified': 0
    }
    
    # حسب الفئة
    for r in db.query("""
        SELECT ifrs18_category, COUNT(*) as c 
        FROM accounts 
        WHERE is_leaf = 1 
        GROUP BY ifrs18_category
    """):
        key = r['ifrs18_category'] or 'UNCLASSIFIED'
        stats['categories'][key] = r['c']
    
    # حسب subcategory
    for r in db.query("""
        SELECT ifrs18_subcategory, COUNT(*) as c 
        FROM accounts 
        WHERE is_leaf = 1 AND ifrs18_subcategory IS NOT NULL AND ifrs18_subcategory != ''
        GROUP BY ifrs18_subcategory
    """):
        stats['subcategories'][r['ifrs18_subcategory']] = r['c']
    
    # حسب القائمة
    for r in db.query("""
        SELECT ifrs18_statement, COUNT(*) as c 
        FROM accounts 
        WHERE is_leaf = 1 
        GROUP BY ifrs18_statement
    """):
        key = r['ifrs18_statement'] or 'UNCLASSIFIED'
        stats['statements'][key] = r['c']
    
    # الإجمالي
    stats['total'] = db.query(
        "SELECT COUNT(*) as c FROM accounts WHERE is_leaf = 1", one=True
    )['c']
    
    stats['unclassified'] = db.query(
        """SELECT COUNT(*) as c FROM accounts 
           WHERE is_leaf = 1 AND (ifrs18_category IS NULL OR ifrs18_category = '')""",
        one=True
    )['c']
    
    return jsonify({'success': True, 'stats': stats})


@fin_bp.route('/ifrs18/update', methods=['POST'])
def ifrs18_update():
    """تحديث تصنيف حساب واحد أو أكثر"""
    data = request.get_json()
    
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    updates = data['updates']
    updated = 0
    errors = []
    
    for u in updates:
        code = u.get('code')
        if not code:
            continue
        
        try:
            fields = []
            values = []
            
            if 'ifrs18_category' in u:
                fields.append("ifrs18_category = ?")
                values.append(u['ifrs18_category'] or None)
            
            if 'ifrs18_subcategory' in u:
                fields.append("ifrs18_subcategory = ?")
                values.append(u['ifrs18_subcategory'] or None)
            
            if 'ifrs18_statement' in u:
                fields.append("ifrs18_statement = ?")
                values.append(u['ifrs18_statement'] or None)
            
            if not fields:
                continue
            
            values.append(code)
            
            sql = f"UPDATE accounts SET {', '.join(fields)} WHERE code = ?"
            db.execute(sql, tuple(values))
            updated += 1
        except Exception as e:
            errors.append(f"{code}: {str(e)[:50]}")
    
    return jsonify({
        'success': True,
        'message': f'تم تحديث {updated} حساب',
        'updated': updated,
        'errors': errors
    })




# ============================================================
# القوائم المالية المقارنة (Comparative Statements)
# ============================================================
@fin_bp.route('/comparative/income-statement', methods=['GET'])
def comparative_income_statement():
    p1_from = request.args.get('period1_from')
    p1_to = request.args.get('period1_to')
    p2_from = request.args.get('period2_from')
    p2_to = request.args.get('period2_to')

    def calc_period(df, dt):
        with db.get_connection() as conn:
            accounts = _get_balance_per_account(conn, df, dt)
        revenue, cogs, selling, admin, depreciation, other_opex = [], [], [], [], [], []
        investing_income, investing_loss, finance_costs, taxes = [], [], [], []
        for a in accounts:
            if a['level'] == 'L1': continue
            td = float(a['period_debit'] or 0)
            tc = float(a['period_credit'] or 0)
            if td == 0 and tc == 0: continue
            code = a['code']
            cat = (a.get('ifrs18_category') or '').upper()
            sub = (a.get('ifrs18_subcategory') or '').upper()
            stmt = (a.get('ifrs18_statement') or '').upper()
            nature = a.get('nature', 'D')
            if stmt == 'BS' and not code.startswith(('4', '5', '6', '7')): continue
            balance = (td - tc) if nature == 'D' else (tc - td)
            if abs(balance) < 0.01: continue
            row = {'code': code, 'name_ar': a['name_ar'], 'amount': round(balance, 2)}
            if cat == 'OPERATING':
                if sub == 'REVENUE': revenue.append(row)
                elif sub == 'COGS': cogs.append(row)
                elif sub == 'SELLING': selling.append(row)
                elif sub == 'ADMIN': admin.append(row)
                elif sub == 'DEPRECIATION': depreciation.append(row)
                else: other_opex.append(row)
            elif cat == 'INVESTING':
                if sub in ('GAIN_ON_SALE', 'INTEREST_INCOME', 'INVESTMENT_INCOME', 'RENTAL_INCOME', 'ROYALTY_INCOME', 'FX_GAIN'):
                    investing_income.append(row)
                else:
                    row['amount'] = -abs(row['amount'])
                    investing_loss.append(row)
            elif cat == 'FINANCING':
                finance_costs.append(row)
            elif cat == 'TAX':
                taxes.append(row)
        tr = sum(r['amount'] for r in revenue)
        tcg = sum(r['amount'] for r in cogs)
        tselling = sum(r['amount'] for r in selling)
        tadmin = sum(r['amount'] for r in admin)
        tdepr = sum(r['amount'] for r in depreciation)
        tother = sum(r['amount'] for r in other_opex)
        t_opex = tselling + tadmin + tdepr + tother
        t_inv_inc = sum(r['amount'] for r in investing_income)
        t_inv_loss = sum(r['amount'] for r in investing_loss)
        t_inv = t_inv_inc + t_inv_loss
        t_fin = sum(r['amount'] for r in finance_costs)
        t_tax = sum(r['amount'] for r in taxes)
        gp = tr - tcg
        op = gp - t_opex
        ebit = op + t_inv
        pbt = ebit - t_fin
        np = pbt - t_tax
        return {
            'revenue': revenue, 'cogs': cogs, 'selling': selling,
            'admin': admin, 'depreciation': depreciation, 'other_opex': other_opex,
            'investing_income': investing_income, 'investing_loss': investing_loss,
            'finance_costs': finance_costs, 'taxes': taxes,
            'totals': {
                'total_revenue': round(tr, 2), 'total_cogs': round(tcg, 2),
                'total_selling': round(tselling, 2), 'total_admin': round(tadmin, 2),
                'total_depreciation': round(tdepr, 2), 'total_opex': round(t_opex, 2),
                'gross_profit': round(gp, 2), 'operating_profit': round(op, 2),
                'total_investing': round(t_inv, 2), 'ebit': round(ebit, 2),
                'total_finance': round(t_fin, 2), 'profit_before_tax': round(pbt, 2),
                'total_taxes': round(t_tax, 2), 'net_profit': round(np, 2),
            }
        }

    period1 = calc_period(p1_from, p1_to)
    period2 = calc_period(p2_from, p2_to)

    return jsonify({
        'success': True,
        'data': {
            'period1': period1,
            'period2': period2,
            'period1_dates': {'from': p1_from, 'to': p1_to},
            'period2_dates': {'from': p2_from, 'to': p2_to},
        }
    })


@fin_bp.route('/comparative/balance-sheet', methods=['GET'])
def comparative_balance_sheet():
    as_of1 = request.args.get('as_of1')
    as_of2 = request.args.get('as_of2')

    def calc_bs(as_of):
        with db.get_connection() as conn:
            accounts = _get_balance_per_account(conn, None, as_of)
        assets, liabilities, equity = [], [], []
        for a in accounts:
            if a['level'] == 'L1': continue
            od = float(a['opening_debit'] or 0)
            oc = float(a['opening_credit'] or 0)
            pd = float(a['period_debit'] or 0)
            pc = float(a['period_credit'] or 0)
            total_debit = od + pd
            total_credit = oc + pc
            if total_debit == 0 and total_credit == 0: continue
            code = a['code']
            nature = a.get('nature', 'D')
            if code.startswith(('4', '5', '6', '7')): continue
            balance = (total_debit - total_credit) if nature == 'D' else (total_credit - total_debit)
            if abs(balance) < 0.01: continue
            row = {'code': code, 'name_ar': a['name_ar'], 'level': a['level'], 'balance': round(balance, 2)}
            if code.startswith('1'):
                if code.startswith('112') or code.startswith('113'):
                    row['balance'] = -abs(row['balance'])
                assets.append(row)
            elif code.startswith('2'):
                liabilities.append(row)
            elif code.startswith('3'):
                equity.append(row)
        ta = sum(r['balance'] for r in assets)
        tl = sum(r['balance'] for r in liabilities)
        te = sum(r['balance'] for r in equity)
        return {
            'assets': assets, 'liabilities': liabilities, 'equity': equity,
            'totals': {
                'assets': round(ta, 2), 'liabilities': round(tl, 2),
                'equity': round(te, 2), 'liab_plus_equity': round(tl + te, 2),
                'balanced': abs(ta - (tl + te)) < 0.01
            }
        }

    period1 = calc_bs(as_of1)
    period2 = calc_bs(as_of2)

    return jsonify({
        'success': True,
        'data': {
            'period1': period1, 'period2': period2,
            'period1_date': as_of1, 'period2_date': as_of2,
        }
    })


@fin_bp.route('/comparative/trial-balance', methods=['GET'])
def comparative_trial_balance():
    p1_from = request.args.get('period1_from')
    p1_to = request.args.get('period1_to')
    p2_from = request.args.get('period2_from')
    p2_to = request.args.get('period2_to')

    def calc_tb(df, dt):
        with db.get_connection() as conn:
            accounts = _get_balance_per_account(conn, df, dt)
        result = []
        for a in accounts:
            od = float(a['opening_debit'] or 0)
            oc = float(a['opening_credit'] or 0)
            pd = float(a['period_debit'] or 0)
            pc = float(a['period_credit'] or 0)
            if od == 0 and oc == 0 and pd == 0 and pc == 0: continue
            is_debit_nature = (a['nature'] == 'D')
            opening_net = (od - oc) if is_debit_nature else (oc - od)
            period_net = (pd - pc) if is_debit_nature else (pc - pd)
            closing_net = opening_net + period_net
            if is_debit_nature:
                od_col = opening_net if opening_net > 0 else 0
                oc_col = abs(opening_net) if opening_net < 0 else 0
                cd_col = closing_net if closing_net > 0 else 0
                cc_col = abs(closing_net) if closing_net < 0 else 0
            else:
                oc_col = opening_net if opening_net > 0 else 0
                od_col = abs(opening_net) if opening_net < 0 else 0
                cc_col = closing_net if closing_net > 0 else 0
                cd_col = abs(closing_net) if closing_net < 0 else 0
            result.append({
                'code': a['code'], 'name_ar': a['name_ar'], 'level': a['level'],
                'nature': a['nature'], 'ifrs18_category': a.get('ifrs18_category') or '',
                'opening_debit': round(od_col, 2), 'opening_credit': round(oc_col, 2),
                'period_debit': round(pd, 2), 'period_credit': round(pc, 2),
                'closing_debit': round(cd_col, 2), 'closing_credit': round(cc_col, 2),
            })
        return result

    period1 = calc_tb(p1_from, p1_to)
    period2 = calc_tb(p2_from, p2_to)

    return jsonify({'success': True, 'data': {'period1': period1, 'period2': period2}})

# ============================================================
# قائمة التدفقات النقدية (IAS 7) — الطريقة غير المباشرة
# ============================================================
def _calc_cash_flow(df, dt):
    """حساب قائمة التدفقات النقدية حسب IAS 7"""
    with db.get_connection() as conn:
        # 1) أرصدة كل الحسابات
        accounts = _get_balance_per_account(conn, df, dt)

    # ============================================================
    # 1) حساب صافي الربح (من قائمة الدخل)
    # ============================================================
    revenue = 0; cogs = 0; opex = 0; investing_income = 0
    finance_costs = 0; taxes = 0; depreciation = 0

    for a in accounts:
        if a['level'] == 'L1':
            continue
        td = float(a['period_debit'] or 0)
        tc = float(a['period_credit'] or 0)
        if td == 0 and tc == 0:
            continue

        code = a['code']
        cat = (a.get('ifrs18_category') or '').upper()
        sub = (a.get('ifrs18_subcategory') or '').upper()
        stmt = (a.get('ifrs18_statement') or '').upper()
        nature = a.get('nature', 'D')

        if stmt == 'BS' and not code.startswith(('4', '5', '6', '7')):
            continue

        balance = (td - tc) if nature == 'D' else (tc - td)
        if abs(balance) < 0.01:
            continue

        if cat == 'OPERATING':
            if sub == 'REVENUE': revenue += balance
            elif sub == 'COGS': cogs += balance
            elif sub == 'DEPRECIATION': depreciation += balance
            else: opex += balance
        elif cat == 'INVESTING':
            investing_income += balance
        elif cat == 'FINANCING':
            finance_costs += balance
        elif cat == 'TAX':
            taxes += balance

    net_profit = revenue - cogs - opex - depreciation + investing_income - finance_costs - taxes

    # ============================================================
    # 2) الإهلاك (يُضاف لأنّه غير نقدي)
    # ============================================================
    # حساب الإهلاك من الحسابات 53xx
    depreciation = 0
    for a in accounts:
        code = a['code']
        if code.startswith('53'):
            td = float(a['period_debit'] or 0)
            tc = float(a['period_credit'] or 0)
            depreciation += (td - tc)

    # ============================================================
    # 3) التغير في رأس المال العامل
    # ============================================================
    # أرصدة أول الفترة (opening)
    # أرصدة آخر الفترة (closing = opening + period)

    def get_account_balance(code_prefix):
        """يرجّع رصيد opening + period لحساب أو مجموعة"""
        total = 0
        for a in accounts:
            if a['code'].startswith(code_prefix):
                od = float(a['opening_debit'] or 0)
                oc = float(a['opening_credit'] or 0)
                pd = float(a['period_debit'] or 0)
                pc = float(a['period_credit'] or 0)
                total_debit = od + pd
                total_credit = oc + pc
                nature = a.get('nature', 'D')
                if nature == 'D':
                    total += (total_debit - total_credit)
                else:
                    total += (total_credit - total_debit)
        return total

    # التغير في المخزون (123x) — زيادة = استخدام نقدي
    inventory = get_account_balance('123')

    # التغير في العملاء (1221) — زيادة = استخدام نقدي
    receivables = get_account_balance('1221')

    # التغير في الموردين (2211) — زيادة = مصدر نقدي
    payables = get_account_balance('2211')

    # ملاحظة: هذه الأرصدة هي أرصدة آخر الفترة (closing)
    # التغير = closing - opening، لكن لأننا نحسب من period فقط
    # سنستخدم أرصدة period كتقدير للتغير

    # التغير في المخزون = period_net
    inventory_change = inventory  # من period

    # التغير في العملاء = period_net
    receivables_change = receivables

    # التغير في الموردين = period_net
    payables_change = payables

    # ============================================================
    # 4) الأنشطة الاستثمارية
    # ============================================================
    # شراء أصول ثابتة (11xx) — مدين = شراء
    fixed_assets_purchased = 0
    fixed_assets_sold = 0

    for a in accounts:
        code = a['code']
        if code.startswith('11'):
            pd = float(a['period_debit'] or 0)
            pc = float(a['period_credit'] or 0)
            fixed_assets_purchased += pd
            fixed_assets_sold += pc

    # إيرادات استثمارية
    investing_income_cash = 0
    for a in accounts:
        cat = (a.get('ifrs18_category') or '').upper()
        if cat == 'INVESTING':
            td = float(a['period_debit'] or 0)
            tc = float(a['period_credit'] or 0)
            nature = a.get('nature', 'D')
            balance = (td - tc) if nature == 'D' else (tc - td)
            investing_income_cash += balance

    # ============================================================
    # 5) الأنشطة التمويلية
    # ============================================================
    loans_received = 0
    loans_paid = 0
    capital_raised = 0

    for a in accounts:
        code = a['code']
        # القروض (21xx)
        if code.startswith('21'):
            pd = float(a['period_debit'] or 0)
            pc = float(a['period_credit'] or 0)
            loans_received += pc
            loans_paid += pd
        # رأس المال (31xx)
        if code.startswith('31') and code.startswith('3101'):
            pc = float(a['period_credit'] or 0)
            pd = float(a['period_debit'] or 0)
            capital_raised += (pc - pd)

    # تكاليف التمويل (مصروفات نقدية)
    finance_costs_cash = 0
    for a in accounts:
        cat = (a.get('ifrs18_category') or '').upper()
        if cat == 'FINANCING':
            td = float(a['period_debit'] or 0)
            tc = float(a['period_credit'] or 0)
            finance_costs_cash += (td - tc)

    # ============================================================
    # 6) حساب صافي التدفقات
    # ============================================================
    # الأنشطة التشغيلية
    operating_cf = (
        net_profit
        + depreciation
        - inventory_change      # زيادة المخزون = استخدام
        - receivables_change    # زيادة العملاء = استخدام
        + payables_change       # زيادة الموردين = مصدر
    )

    # الأنشطة الاستثمارية
    investing_cf = (
        -fixed_assets_purchased
        + fixed_assets_sold
        + investing_income_cash
    )

    # الأنشطة التمويلية
    financing_cf = (
        +loans_received
        - loans_paid
        + capital_raised
        - finance_costs_cash
    )

    # صافي التغير في النقدية
    net_change = operating_cf + investing_cf + financing_cf

    # النقدية أول الفترة
    cash_opening = 0
    for a in accounts:
        if a['code'].startswith('121'):
            od = float(a['opening_debit'] or 0)
            oc = float(a['opening_credit'] or 0)
            cash_opening += (od - oc)

    # النقدية آخر الفترة
    cash_closing = cash_opening + net_change

    # للتحقق: حساب النقدية الفعلي
    cash_actual = 0
    for a in accounts:
        if a['code'].startswith('121'):
            od = float(a['opening_debit'] or 0)
            oc = float(a['opening_credit'] or 0)
            pd = float(a['period_debit'] or 0)
            pc = float(a['period_credit'] or 0)
            cash_actual += (od + pd - oc - pc)

    return {
        'net_profit': round(net_profit, 2),
        'depreciation': round(depreciation, 2),
        'working_capital': {
            'inventory_change': round(-inventory_change, 2),
            'receivables_change': round(-receivables_change, 2),
            'payables_change': round(payables_change, 2),
        },
        'operating_activities': round(operating_cf, 2),
        'investing_activities': {
            'fixed_assets_purchased': round(-fixed_assets_purchased, 2),
            'fixed_assets_sold': round(fixed_assets_sold, 2),
            'investing_income': round(investing_income_cash, 2),
            'total': round(investing_cf, 2),
        },
        'financing_activities': {
            'loans_received': round(loans_received, 2),
            'loans_paid': round(-loans_paid, 2),
            'capital_raised': round(capital_raised, 2),
            'finance_costs': round(-finance_costs_cash, 2),
            'total': round(financing_cf, 2),
        },
        'net_change': round(net_change, 2),
        'cash_opening': round(cash_opening, 2),
        'cash_closing': round(cash_closing, 2),
        'cash_actual': round(cash_actual, 2),
        'balanced': abs(cash_closing - cash_actual) < 0.01,
    }


@fin_bp.route('/cash-flow', methods=['GET'])
def cash_flow():
    """قائمة التدفقات النقدية — الطريقة غير المباشرة"""
    df = request.args.get('date_from')
    dt = request.args.get('date_to')
    as_of = request.args.get('as_of')

    if as_of and not dt:
        dt = as_of

    result = _calc_cash_flow(df, dt)

    return jsonify({
        'success': True,
        'data': result,
        'period': {'from': df, 'to': dt}
    })


@fin_bp.route('/comparative/cash-flow', methods=['GET'])
def comparative_cash_flow():
    """قائمة التدفقات النقدية المقارنة"""
    p1_from = request.args.get('period1_from')
    p1_to = request.args.get('period1_to')
    p2_from = request.args.get('period2_from')
    p2_to = request.args.get('period2_to')

    period1 = _calc_cash_flow(p1_from, p1_to)
    period2 = _calc_cash_flow(p2_from, p2_to)

    return jsonify({
        'success': True,
        'data': {
            'period1': period1,
            'period2': period2,
        }
    })
