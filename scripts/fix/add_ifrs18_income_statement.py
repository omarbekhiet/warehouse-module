# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# إزالة أي دالة income-statement قديمة
pattern = re.compile(r"@report_bp\.route\('/income-statement'.*?(?=@report_bp\.route|$)", re.DOTALL)
content = pattern.sub("", content)

# إضافة دالة جديدة
new_func = """
@report_bp.route('/income-statement', methods=['GET'])
def income_statement():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    try:
        with db.get_connection() as conn:
            # 1. جلب كل الحسابات التي عليها حركات (أو كل الحسابات ثم فلترتها)
            accounts = conn.execute(\"\"\"SELECT code, name_ar, financial_statement, pl_group FROM accounts WHERE financial_statement = 'IS' ORDER BY code\"\"\").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                acc_dict[code] = {
                    'code': code,
                    'name': a['name_ar'],
                    'pl_group': a['pl_group'], # قد يكون فارغاً
                    'opening_balance': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0
                }

            # 2. جلب الأرصدة من القيود
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

            # 3. التجميع (Roll-up) (اختياري: للحسابات الآباء فقط)
            # (يمكن تخطي هذه الخطوة إذا أردنا عرض الحسابات الورقية فقط)

            # 4. تصنيف الحسابات حسب IFRS 18
            sections = {
                'operating': {'name': 'قسم التشغيل (Operating)', 'items': [], 'total': 0.0},
                'investing': {'name': 'قسم الاستثمار (Investing)', 'items': [], 'total': 0.0},
                'financing': {'name': 'قسم التمويل (Financing)', 'items': [], 'total': 0.0},
                'taxes': {'name': 'قسم الضرائب (Income Taxes)', 'items': [], 'total': 0.0},
                'discontinued': {'name': 'قسم العمليات المتوقفة (Discontinued Operations)', 'items': [], 'total': 0.0},
            }

            for code, node in acc_dict.items():
                balance = node['opening_balance'] + node['period_debit'] - node['period_credit']
                # تخطي الحسابات التي رصيدها صفر
                if abs(balance) < 0.01:
                    continue
                
                item = {'code': code, 'name': node['name'], 'amount': balance}
                
                # التصنيف بناءً على pl_group أو الكود
                group = node['pl_group'] or ''
                if group == 'TAX' or code.startswith('7'):
                    sections['taxes']['items'].append(item)
                    sections['taxes']['total'] += balance
                elif group == 'FIN' or code.startswith('6'):
                    sections['financing']['items'].append(item)
                    sections['financing']['total'] += balance
                elif group == 'INV' or code.startswith('42'):
                    sections['investing']['items'].append(item)
                    sections['investing']['total'] += balance
                elif group == 'DISC':
                    sections['discontinued']['items'].append(item)
                    sections['discontinued']['total'] += balance
                else:
                    # كل ما تبقى يذهب إلى التشغيل (الافتراضي)
                    sections['operating']['items'].append(item)
                    sections['operating']['total'] += balance

            # 5. بناء النتيجة النهائية
            return jsonify({
                'success': True,
                'data': {
                    'sections': sections,
                    'net_profit': sum(s['total'] for s in sections.values())
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
"""

content += new_func

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم إضافة دالة income-statement الجديدة (تقرأ من ميزان المراجعة وتصنف حسب IFRS 18).")
