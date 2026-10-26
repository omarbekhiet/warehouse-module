# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# 1. إزالة أي دوال قديمة متبقية (لتنظيف)
for endpoint in ['trial-balance', 'balance-sheet', 'income-statement', 'cash-flow']:
    pattern = re.compile(r"@report_bp\.route\('/" + endpoint + r"'.*?(?=@report_bp\.route|$)", re.DOTALL)
    content = pattern.sub("", content)

# 2. إضافة الدوال الأربعة في نهاية الملف

new_code = """

# ============================================================
# ميزان المراجعة (Trial Balance)
# ============================================================
@report_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                acc_dict[code] = {
                    'code': code, 'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl, 'opening_balance': 0.0, 'period_debit': 0.0, 'period_credit': 0.0
                }

            if from_date:
                q_open = \"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                             FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                             WHERE je.status = 'POSTED' AND je.entry_date < ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
                for r in conn.execute(q_open, (from_date,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['opening_balance'] = float(r['d']) - float(r['c'])

            cond, vals = ["je.status = 'POSTED'", "jl.account_code IS NOT NULL"], []
            if from_date:
                cond.append("je.entry_date >= ?"); vals.append(from_date)
            if to_date:
                cond.append("je.entry_date <= ?"); vals.append(to_date)
            where = " AND ".join(cond)

            q_period = f\"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                            FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                            WHERE {where} GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
            for r in conn.execute(q_period, tuple(vals)).fetchall():
                c = str(r['acc_code']).strip()
                if c in acc_dict:
                    acc_dict[c]['period_debit'] = float(r['d'])
                    acc_dict[c]['period_credit'] = float(r['c'])

            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['opening_balance'] += node['opening_balance']
                    acc_dict[parent]['period_debit'] += node['period_debit']
                    acc_dict[parent]['period_credit'] += node['period_credit']

            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                result.append(node)

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# الميزانية العمومية (Balance Sheet)
# ============================================================
@report_bp.route('/financial-reports/balance-sheet', methods=['GET'])
def balance_sheet_report():
    as_of = request.args.get('as_of')
    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                acc_dict[code] = {'code': code, 'name': a['name_ar'], 'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None, 'level': lvl, 'balance': 0.0}

            if as_of:
                q = \"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                       FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                       WHERE je.status = 'POSTED' AND je.entry_date <= ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
                for r in conn.execute(q, (as_of,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict: acc_dict[c]['balance'] = float(r['bal'])

            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict: acc_dict[parent]['balance'] += node['balance']

            assets, liabilities, equity = [], [], []
            for code, node in acc_dict.items():
                if code.startswith('1'): assets.append(node)
                elif code.startswith('2'): node['balance'] = -node['balance']; liabilities.append(node)
                elif code.startswith('3'): node['balance'] = -node['balance']; equity.append(node)

            t_assets = acc_dict.get('1', {}).get('balance', 0.0)
            t_liab = abs(acc_dict.get('2', {}).get('balance', 0.0))
            t_eq = abs(acc_dict.get('3', {}).get('balance', 0.0))

            return jsonify({
                'success': True,
                'data': {
                    'assets': sorted(assets, key=lambda x: x['code']),
                    'liabilities': sorted(liabilities, key=lambda x: x['code']),
                    'equity': sorted(equity, key=lambda x: x['code']),
                    'totals': {'assets': t_assets, 'liabilities': t_liab, 'equity': t_eq, 'liab_plus_equity': t_liab + t_eq, 'balanced': abs(t_assets - (t_liab + t_eq)) < 0.01}
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# قائمة الدخل (Income Statement)
# ============================================================
@report_bp.route('/reports/income-statement', methods=['GET'])
def income_statement():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    cond, vals = [], []
    if from_date: cond.append("je.entry_date >= ?"); vals.append(from_date)
    if to_date: cond.append("je.entry_date <= ?"); vals.append(to_date)
    where = " AND ".join(cond) if cond else "1=1"
    try:
        with db.get_connection() as conn:
            query = f\"\"\"SELECT a.code, a.name_ar, a.nature, COALESCE(SUM(jl.debit_amount), 0) as total_debit, COALESCE(SUM(jl.credit_amount), 0) as total_credit
                        FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id JOIN accounts a ON jl.account_code = a.code
                        WHERE je.status = 'POSTED' AND {where} AND a.nature IN ('REVENUE', 'EXPENSE') GROUP BY a.code, a.name_ar, a.nature ORDER BY a.code\"\"\"
            rows = conn.execute(query, vals).fetchall()
            revenues, expenses = [], []
            total_revenue = 0
            total_expense = 0
            for r in rows:
                debit = float(r['total_debit']); credit = float(r['total_credit'])
                if r['nature'] == 'REVENUE':
                    balance = credit - debit
                    if abs(balance) > 0.01:
                        revenues.append({'code': r['code'], 'name': r['name_ar'], 'amount': balance}); total_revenue += balance
                elif r['nature'] == 'EXPENSE':
                    balance = debit - credit
                    if abs(balance) > 0.01:
                        expenses.append({'code': r['code'], 'name': r['name_ar'], 'amount': balance}); total_expense += balance
            net_profit = total_revenue - total_expense
            return jsonify({'success': True, 'data': {'revenues': revenues, 'expenses': expenses, 'total_revenue': total_revenue, 'total_expense': total_expense, 'net_profit': net_profit}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# التدفقات النقدية (Cash Flow)
# ============================================================
@report_bp.route('/financial-reports/cash-flow', methods=['GET'])
def cash_flow_report():
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
                if not limit: return 0.0
                op = '<' if is_lt else '<='
                q = f\"\"\"SELECT COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                        FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                        WHERE je.status = 'POSTED' AND je.entry_date {op} ? AND jl.account_code LIKE ?\"\"\"
                res = conn.execute(q, (limit, prefix + '%')).fetchone()
                return float(res['bal']) if res else 0.0

            def get_change(prefix):
                if not from_date or not to_date: return 0.0
                return get_bal(prefix, to_date) - get_bal(prefix, from_date, True)

            rev_bal = -(get_change('4'))
            cogs_bal = get_change('5')
            exp_bal = get_change('6')
            net_profit = rev_bal - abs(cogs_bal) - abs(exp_bal)
            depreciation = get_change('63')

            inv = get_change('124')
            ar = get_change('123')
            ap = get_change('221')
            wc = -inv - ar + ap

            net_operating = net_profit + depreciation + wc

            fa = get_change('111')
            net_investing = -fa

            cap = get_change('31')
            loans = get_change('211') + get_change('225')
            net_financing = cap + loans

            cash_prefixes = ['121']
            start_cash = sum(get_bal(p, from_date, True) for p in cash_prefixes) if from_date else 0.0
            end_cash = sum(get_bal(p, to_date) for p in cash_prefixes) if to_date else 0.0
            net_change = end_cash - start_cash

            return jsonify({
                'success': True,
                'data': {
                    'start_balance': start_cash, 'end_balance': end_cash, 'net_change': net_change,
                    'net_profit': net_profit, 'depreciation': depreciation,
                    'operating': {'total': net_operating},
                    'investing': {'items': [{'name': 'أصول ثابتة', 'amount': -fa}], 'total': net_investing},
                    'financing': {'items': [{'name': 'رأس المال', 'amount': cap}, {'name': 'قروض', 'amount': loans}], 'total': net_financing}
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
"""

content += new_code

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم إضافة الدوال الأربعة (ميزان المراجعة، الميزانية، قائمة الدخل، التدفقات النقدية) إلى السيرفر.")
