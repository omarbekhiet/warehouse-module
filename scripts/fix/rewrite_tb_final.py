# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# 1. إزالة دالة trial_balance القديمة بالكامل
pattern = re.compile(r"@report_bp\.route\('/trial-balance'.*?(?=@report_bp\.route|$)", re.DOTALL)
content = pattern.sub("", content)

# 2. كتابة دالة trial_balance جديدة من الصفر مع الفلترة
new_func = """
@report_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    level_filter = request.args.get('level')  # المستوى المطلوب

    try:
        with db.get_connection() as conn:
            # جلب كل الحسابات
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try:
                    lvl = int(lvl_str)
                except Exception:
                    lvl = 1

                acc_dict[code] = {
                    'code': code,
                    'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl,
                    'opening_balance': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0
                }

            # الرصيد الافتتاحي
            if from_date:
                q_open = \"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                             FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                             WHERE je.status = 'POSTED' AND je.entry_date < ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
                for r in conn.execute(q_open, (from_date,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['opening_balance'] = float(r['d']) - float(r['c'])

            # حركات الفترة
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

            # التجميع (Roll-up)
            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['opening_balance'] += node['opening_balance']
                    acc_dict[parent]['period_debit'] += node['period_debit']
                    acc_dict[parent]['period_credit'] += node['period_credit']

            # بناء النتيجة مع الفلترة
            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                
                # الفلترة: إذا تم تحديد مستوى، نعرض فقط الحسابات التي تنتمي لهذا المستوى
                if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] != target_level:
                            continue
                    except ValueError:
                        pass
                
                result.append(node)

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
"""

content += new_func

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم إعادة كتابة دالة trial_balance بالكامل مع الفلترة الصارمة.")
