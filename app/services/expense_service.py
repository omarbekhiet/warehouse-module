"""
خدمة إدارة صرف النثريات
"""
from app.database import db
from app.utils import json_safe
from app.services.settings_service import get_accounting, get_cash
from datetime import datetime


class ExpenseService:
    """خدمة صرف النثريات"""

    # =========================================
    # Expense Categories
    # =========================================

    def list_categories(self, only_active=True):
        sql = """
            SELECT ec.*, a.name_ar as account_name
            FROM expense_categories ec
            LEFT JOIN accounts a ON ec.account_code = a.code
            WHERE 1=1
        """
        if only_active:
            sql += " AND ec.is_active = 1"
        sql += " ORDER BY ec.code"

        rows = db.query(sql)
        return [dict(r) for r in rows]

    def create_category(self, data):
        if not data.get('name_ar') or not data.get('account_code'):
            return {'success': False, 'message': 'الاسم والحساب مطلوبان'}

        code = data.get('code')
        if not code:
            rows = db.query("SELECT code FROM expense_categories WHERE code LIKE 'EXP-%' ORDER BY id DESC LIMIT 1")
            if rows:
                try:
                    n = int(rows[0]['code'].split('-')[-1]) + 1
                except:
                    n = 1
            else:
                n = 1
            code = f"EXP-{n:03d}"

        exists = db.query("SELECT id FROM expense_categories WHERE code = ?", (code,), one=True)
        if exists:
            return {'success': False, 'message': 'الكود مستخدم'}

        cid = db.execute("""
            INSERT INTO expense_categories (code, name_ar, name_en, account_code, parent_id, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, data['name_ar'], data.get('name_en'),
              data['account_code'], data.get('parent_id'), data.get('notes')))

        return {'success': True, 'data': {'id': cid, 'code': code}}

    # =========================================
    # Expenses
    # =========================================

    def create_expense(self, data, user_id=1):
        """إنشاء مصروف جديد"""
        category_id = data.get('category_id')
        cash_box_id = data.get('cash_box_id')
        amount = float(data.get('amount', 0))
        expense_date = data.get('expense_date') or datetime.now().strftime('%Y-%m-%d')

        if not category_id or not cash_box_id or amount <= 0:
            return {'success': False, 'message': 'بيانات ناقصة أو مبلغ غير صحيح'}

        with db.transaction() as conn:
            cur = conn.cursor()

            # جلب التصنيف
            cur.execute("SELECT * FROM expense_categories WHERE id=?", (category_id,))
            category = cur.fetchone()
            if not category:
                return {'success': False, 'message': 'التصنيف غير موجود'}

            # جلب الخزينة
            cur.execute("SELECT * FROM cash_boxes WHERE id=?", (cash_box_id,))
            box = cur.fetchone()
            if not box:
                return {'success': False, 'message': 'الخزينة غير موجودة'}

            # الرصيد
            current_balance = float(box['current_balance'] or 0)
            if current_balance < amount:
                cash_settings = get_cash()
                if not cash_settings.get('allow_negative_cash', False):
                    return {'success': False, 'message': f'الرصيد غير كافٍ. المتاح: {current_balance:.2f}'}

            # رقم المصروف
            year = datetime.now().year
            cur.execute("SELECT COUNT(*)+1 FROM petty_cash_expenses WHERE strftime('%Y', expense_date)=?", (str(year),))
            n = cur.fetchone()[0]
            expense_no = f"EXP-{year}-{n:06d}"

            # إدخال المصروف
            cur.execute("""
                INSERT INTO petty_cash_expenses
                (expense_no, expense_date, category_id, amount, cash_box_id,
                 beneficiary, description, reference, notes, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'POSTED', ?)
            """, (
                expense_no, expense_date, category_id, amount, cash_box_id,
                data.get('beneficiary'), data.get('description'),
                data.get('reference'), data.get('notes'), user_id
            ))
            expense_id = cur.lastrowid

            # تحديث رصيد الخزينة
            new_balance = current_balance - amount
            cur.execute("UPDATE cash_boxes SET current_balance=? WHERE id=?", (new_balance, cash_box_id))

            # حركة على الخزينة
            cur.execute("""
                INSERT INTO cash_box_transactions
                (box_id, box_type, txn_type, txn_date, amount, balance_after,
                 reference_no, description, created_by)
                VALUES (?, 'CASH_BOX', 'WITHDRAW', ?, ?, ?, ?, ?, ?)
            """, (
                cash_box_id, expense_date, amount, new_balance,
                expense_no, f"مصروف: {category['name_ar']} - {data.get('description', '')}", user_id
            ))
            txn_id = cur.lastrowid

            # القيد المحاسبي
            acc_settings = get_accounting()
            auto_journal = acc_settings.get('auto_journal_receipts', True)
            je_id = None
            je_no = None

            if auto_journal:
                cur.execute("SELECT COUNT(*)+1 FROM journal_entries WHERE strftime('%Y', entry_date)=?", (str(year),))
                je_n = cur.fetchone()[0]
                je_no = f"JE-{year}-{je_n:06d}"

                cur.execute("""
                    INSERT INTO journal_entries
                    (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
                    VALUES (?, ?, 'PETTY_CASH_EXPENSE', ?, ?, ?, 'POSTED')
                """, (je_no, expense_date, expense_id, expense_no, f"صرف: {category['name_ar']}"))
                je_id = cur.lastrowid

                # مدين: حساب المصروف
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 1, ?, ?, ?, 0)
                """, (je_id, category['account_code'], f"مصروف - {category['name_ar']}", amount))

                # دائن: حساب الخزينة
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, 2, ?, 'خزينة - صرف', 0, ?)
                """, (je_id, box['account_code'], amount))

                cur.execute("""
                    UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
                """, (amount, amount, je_id))

                cur.execute("""
                    UPDATE petty_cash_expenses SET journal_entry_id=? WHERE id=?
                """, (je_id, expense_id))

                # ربط القيد بحركة الخزينة
                cur.execute("""
                    UPDATE cash_box_transactions SET journal_entry_id=? WHERE id=?
                """, (je_id, txn_id))

            # التفاصيل (شيك/حوالة/...)
            details = data.get('details', {})
            if details and details.get('payment_type'):
                cur.execute("""
                    INSERT INTO expense_details
                    (expense_id, payment_type, cheque_no, cheque_bank, cheque_date,
                     transfer_no, transfer_bank, card_txn_no, card_last4, card_bank,
                     wallet_name, wallet_txn_no, wallet_phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    expense_id, details.get('payment_type'),
                    details.get('cheque_no'), details.get('cheque_bank'), details.get('cheque_date'),
                    details.get('transfer_no'), details.get('transfer_bank'),
                    details.get('card_txn_no'), details.get('card_last4'), details.get('card_bank'),
                    details.get('wallet_name'), details.get('wallet_txn_no'), details.get('wallet_phone')
                ))

            conn.commit()

            return {
                'success': True,
                'data': {
                    'id': expense_id,
                    'expense_no': expense_no,
                    'amount': amount,
                    'balance_after': new_balance,
                    'journal_entry_id': je_id,
                    'journal_entry_no': je_no,
                    'txn_id': txn_id
                }
            }

    def list_expenses(self, date_from=None, date_to=None, category_id=None, cash_box_id=None, limit=200):
        sql = """
            SELECT e.*,
                   ec.name_ar as category_name,
                   cb.name_ar as box_name,
                   u.full_name as created_by_name
            FROM petty_cash_expenses e
            LEFT JOIN expense_categories ec ON e.category_id = ec.id
            LEFT JOIN cash_boxes cb ON e.cash_box_id = cb.id
            LEFT JOIN users u ON e.created_by = u.id
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND e.expense_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND e.expense_date <= ?"
            params.append(date_to)
        if category_id:
            sql += " AND e.category_id = ?"
            params.append(category_id)
        if cash_box_id:
            sql += " AND e.cash_box_id = ?"
            params.append(cash_box_id)

        sql += " ORDER BY e.expense_date DESC, e.id DESC LIMIT ?"
        params.append(limit)

        rows = db.query(sql, params)
        return [dict(r) for r in rows]

    def get_expense(self, expense_id):
        exp = db.query("""
            SELECT e.*,
                   ec.name_ar as category_name, ec.account_code as category_account,
                   cb.name_ar as box_name, cb.account_code as box_account
            FROM petty_cash_expenses e
            LEFT JOIN expense_categories ec ON e.category_id = ec.id
            LEFT JOIN cash_boxes cb ON e.cash_box_id = cb.id
            WHERE e.id=?
        """, (expense_id,), one=True)

        if not exp:
            return None

        # التفاصيل
        details = db.query("SELECT * FROM expense_details WHERE expense_id=?", (expense_id,), one=True)
        exp = dict(exp)
        exp['details'] = dict(details) if details else None

        return exp

    def delete_expense(self, expense_id):
        with db.transaction() as conn:
            cur = conn.cursor()

            # جلب المصروف
            cur.execute("SELECT * FROM petty_cash_expenses WHERE id=?", (expense_id,))
            exp = cur.fetchone()
            if not exp:
                return {'success': False, 'message': 'غير موجود'}

            # حذف القيد
            if exp['journal_entry_id']:
                cur.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id=?", (exp['journal_entry_id'],))
                cur.execute("DELETE FROM journal_entries WHERE id=?", (exp['journal_entry_id'],))

            # استرجاع رصيد الخزينة
            cur.execute("SELECT current_balance FROM cash_boxes WHERE id=?", (exp['cash_box_id'],))
            box = cur.fetchone()
            if box:
                new_balance = float(box['current_balance'] or 0) + float(exp['amount'])
                cur.execute("UPDATE cash_boxes SET current_balance=? WHERE id=?", (new_balance, exp['cash_box_id']))

            # حذف التفاصيل
            cur.execute("DELETE FROM expense_details WHERE expense_id=?", (expense_id,))

            # حذف حركة الخزينة
            cur.execute("""
                DELETE FROM cash_box_transactions
                WHERE box_id=? AND box_type='CASH_BOX' AND reference_no=?
            """, (exp['cash_box_id'], exp['expense_no']))

            # حذف المصروف
            cur.execute("DELETE FROM petty_cash_expenses WHERE id=?", (expense_id,))

            conn.commit()
            return {'success': True, 'message': 'تم الحذف'}

    def get_stats(self, date_from=None, date_to=None):
        """إحصائيات المصروفات"""
        sql = "SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as total FROM petty_cash_expenses WHERE 1=1"
        params = []
        if date_from:
            sql += " AND expense_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND expense_date <= ?"
            params.append(date_to)

        row = db.query(sql, params, one=True)

        # توزيع حسب التصنيف
        sql2 = """
            SELECT ec.name_ar, ec.code, COUNT(e.id) as cnt, COALESCE(SUM(e.amount), 0) as total
            FROM expense_categories ec
            LEFT JOIN petty_cash_expenses e ON e.category_id = ec.id
        """
        params2 = []
        if date_from or date_to:
            sql2 += " AND (1=1"
            if date_from:
                sql2 += " AND e.expense_date >= ?"
                params2.append(date_from)
            if date_to:
                sql2 += " AND e.expense_date <= ?"
                params2.append(date_to)
            sql2 += ")"

        sql2 += " GROUP BY ec.id ORDER BY total DESC"
        by_category = db.query(sql2, params2)

        return {
            'total_count': row['cnt'],
            'total_amount': float(row['total']),
            'by_category': [dict(r) for r in by_category]
        }


expense_service = ExpenseService()