"""
خدمة إدارة حركات الخزائن والبنوك
"""
from app.database import db
from app.utils import json_safe
from app.services.settings_service import get_cash, get_accounting
from datetime import datetime


class CashBoxService:
    """خدمة حركات الخزائن والبنوك والبطاقات"""
    
    # =========================================
    # Transactions
    # =========================================
    
    def create_transaction(self, data, user_id=1):
        """إنشاء حركة على خزينة/بنك/بطاقة"""
        box_type = data.get('box_type')
        box_id = data.get('box_id')
        txn_type = data.get('txn_type')
        amount = float(data.get('amount', 0))
        txn_date = data.get('txn_date') or datetime.now().strftime('%Y-%m-%d')
        
        if not box_type or not box_id or not txn_type or amount <= 0:
            return {'success': False, 'message': 'بيانات ناقصة أو مبلغ غير صحيح'}
        
        table, _ = self._get_table_for_type(box_type)
        if not table:
            return {'success': False, 'message': 'نوع الخزينة غير صحيح'}
        
        with db.transaction() as conn:
            cur = conn.cursor()
            
            cur.execute(f"SELECT * FROM {table} WHERE id=?", (box_id,))
            box = cur.fetchone()
            if not box:
                return {'success': False, 'message': 'الخزينة غير موجودة'}
            
            current_balance = float(box['current_balance'] or 0)
            
            if txn_type in ('WITHDRAW', 'TRANSFER_OUT') and current_balance < amount:
                settings = get_cash()
                allow_negative = settings.get('allow_negative_cash', False)
                if not allow_negative:
                    return {
                        'success': False,
                        'message': f'الرصيد غير كافٍ. الرصيد الحالي: {current_balance:.2f}'
                    }
            
            if txn_type in ('DEPOSIT', 'TRANSFER_IN'):
                new_balance = current_balance + amount
            else:
                new_balance = current_balance - amount
            
            year = datetime.now().year
            cur.execute(
                "SELECT COUNT(*)+1 FROM cash_box_transactions WHERE strftime('%Y', txn_date)=?",
                (str(year),)
            )
            n = cur.fetchone()[0]
            ref_no = data.get('reference_no') or f"TXN-{year}-{n:06d}"
            
            cur.execute("""
                INSERT INTO cash_box_transactions 
                (box_id, box_type, txn_type, txn_date, amount, balance_after,
                 reference_no, description, related_txn_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                box_id, box_type, txn_type, txn_date, amount, new_balance,
                ref_no, data.get('description'), data.get('related_txn_id'), user_id
            ))
            txn_id = cur.lastrowid
            
            cur.execute(f"UPDATE {table} SET current_balance=? WHERE id=?", (new_balance, box_id))
            
            acc_settings = get_accounting()
            auto_journal = acc_settings.get('auto_journal_receipts', True)
            
            je_id = None
            je_no = None
            if auto_journal:
                je_id, je_no = self._create_journal_entry(
                    conn, txn_type, txn_date, amount,
                    box['account_code'], ref_no,
                    data.get('description') or f"حركة {txn_type} - {ref_no}"
                )
                cur.execute(
                    "UPDATE cash_box_transactions SET journal_entry_id=? WHERE id=?",
                    (je_id, txn_id)
                )
            
            conn.commit()
            
            return {
                'success': True,
                'data': {
                    'id': txn_id,
                    'reference_no': ref_no,
                    'amount': amount,
                    'balance_after': new_balance,
                    'journal_entry_id': je_id,
                    'journal_entry_no': je_no
                }
            }
    
    
    def list_transactions(self, box_type=None, box_id=None, date_from=None, date_to=None, limit=200):
        """قائمة الحركات"""
        sql = """
            SELECT t.*, 
                   CASE t.box_type 
                       WHEN 'CASH_BOX' THEN cb.name_ar
                       WHEN 'BANK' THEN b.name_ar
                       WHEN 'CARD' THEN c.name_ar
                   END as box_name
            FROM cash_box_transactions t
            LEFT JOIN cash_boxes cb ON t.box_type='CASH_BOX' AND t.box_id = cb.id
            LEFT JOIN banks b ON t.box_type='BANK' AND t.box_id = b.id
            LEFT JOIN payment_cards c ON t.box_type='CARD' AND t.box_id = c.id
            WHERE 1=1
        """
        params = []
        if box_type:
            sql += " AND t.box_type = ?"
            params.append(box_type)
        if box_id:
            sql += " AND t.box_id = ?"
            params.append(box_id)
        if date_from:
            sql += " AND t.txn_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND t.txn_date <= ?"
            params.append(date_to)
        sql += " ORDER BY t.txn_date DESC, t.id DESC LIMIT ?"
        params.append(limit)
        
        rows = db.query(sql, params)
        return [dict(r) for r in rows]
    
    
    def transfer_between_boxes(self, data, user_id=1):
        """تحويل بين خزنتين"""
        from_box_type = data.get('from_box_type')
        from_box_id = data.get('from_box_id')
        to_box_type = data.get('to_box_type')
        to_box_id = data.get('to_box_id')
        amount = float(data.get('amount', 0))
        txn_date = data.get('txn_date') or datetime.now().strftime('%Y-%m-%d')
        description = data.get('description') or 'تحويل بين خزنتين'
        
        if not all([from_box_type, from_box_id, to_box_type, to_box_id]) or amount <= 0:
            return {'success': False, 'message': 'بيانات ناقصة'}
        
        if from_box_type == to_box_type and from_box_id == to_box_id:
            return {'success': False, 'message': 'لا يمكن التحويل لنفس الخزينة'}
        
        with db.transaction() as conn:
            cur = conn.cursor()
            
            from_table, _ = self._get_table_for_type(from_box_type)
            to_table, _ = self._get_table_for_type(to_box_type)
            
            cur.execute(f"SELECT * FROM {from_table} WHERE id=?", (from_box_id,))
            from_box = cur.fetchone()
            cur.execute(f"SELECT * FROM {to_table} WHERE id=?", (to_box_id,))
            to_box = cur.fetchone()
            
            if not from_box or not to_box:
                return {'success': False, 'message': 'إحدى الخزائن غير موجودة'}
            
            from_balance = float(from_box['current_balance'] or 0)
            to_balance = float(to_box['current_balance'] or 0)
            
            if from_balance < amount:
                settings = get_cash()
                if not settings.get('allow_negative_cash', False):
                    return {
                        'success': False,
                        'message': f'الرصيد غير كافٍ في الخزينة المصدر. المتاح: {from_balance:.2f}'
                    }
            
            year = datetime.now().year
            cur.execute("SELECT COUNT(*)+1 FROM cash_box_transactions")
            n = cur.fetchone()[0]
            transfer_ref = f"TRF-{year}-{n:06d}"
            
            cur.execute("""
                INSERT INTO cash_box_transactions 
                (box_id, box_type, txn_type, txn_date, amount, balance_after,
                 reference_no, description, created_by)
                VALUES (?, ?, 'TRANSFER_OUT', ?, ?, ?, ?, ?, ?)
            """, (
                from_box_id, from_box_type, txn_date, amount, from_balance - amount,
                transfer_ref, f"{description} → {to_box['name_ar']}", user_id
            ))
            out_txn_id = cur.lastrowid
            
            cur.execute("""
                INSERT INTO cash_box_transactions 
                (box_id, box_type, txn_type, txn_date, amount, balance_after,
                 reference_no, description, related_txn_id, created_by)
                VALUES (?, ?, 'TRANSFER_IN', ?, ?, ?, ?, ?, ?, ?)
            """, (
                to_box_id, to_box_type, txn_date, amount, to_balance + amount,
                transfer_ref, f"{description} ← {from_box['name_ar']}", out_txn_id, user_id
            ))
            in_txn_id = cur.lastrowid
            
            cur.execute(
                "UPDATE cash_box_transactions SET related_txn_id=? WHERE id=?",
                (in_txn_id, out_txn_id)
            )
            
            cur.execute(f"UPDATE {from_table} SET current_balance=? WHERE id=?", (from_balance - amount, from_box_id))
            cur.execute(f"UPDATE {to_table} SET current_balance=? WHERE id=?", (to_balance + amount, to_box_id))
            
            acc_settings = get_accounting()
            je_id = None
            je_no = None
            if acc_settings.get('auto_journal_receipts', True):
                je_id, je_no = self._create_transfer_journal(
                    conn, txn_date, amount, from_box['account_code'],
                    to_box['account_code'], transfer_ref, description
                )
                
                # ربط القيد بالحركتين
                if je_id:
                    cur.execute(
                        "UPDATE cash_box_transactions SET journal_entry_id=? WHERE id=?",
                        (je_id, out_txn_id)
                    )
                    cur.execute(
                        "UPDATE cash_box_transactions SET journal_entry_id=? WHERE id=?",
                        (je_id, in_txn_id)
                    )

            return {
                'success': True,
                'data': {
                    'reference_no': transfer_ref,
                    'out_txn_id': out_txn_id,
                    'in_txn_id': in_txn_id,
                    'amount': amount,
                    'from_balance_after': from_balance - amount,
                    'to_balance_after': to_balance + amount,
                    'journal_entry_id': je_id,
                    'journal_entry_no': je_no
                }
            }
    
    
    # =========================================
    # Helpers
    # =========================================
    
    def _get_table_for_type(self, box_type):
        mapping = {
            'CASH_BOX': ('cash_boxes', 'CASH'),
            'BANK': ('banks', 'BANK'),
            'CARD': ('payment_cards', 'CARD')
        }
        return mapping.get(box_type, (None, None))
    
    
    def _create_journal_entry(self, conn, txn_type, date, amount, cash_account, ref_no, description):
        cur = conn.cursor()
        year = datetime.now().year
        
        cur.execute(
            "SELECT COUNT(*)+1 FROM journal_entries WHERE strftime('%Y', entry_date)=?",
            (str(year),)
        )
        n = cur.fetchone()[0]
        je_no = f"JE-{year}-{n:06d}"
        
        cur.execute("""
            INSERT INTO journal_entries 
            (entry_no, entry_date, reference_type, reference_no, description, status)
            VALUES (?, ?, 'CASH_BOX_TXN', ?, ?, 'POSTED')
        """, (je_no, date, ref_no, description))
        je_id = cur.lastrowid
        
        if txn_type in ('DEPOSIT', 'TRANSFER_IN'):
            cur.execute("""
                INSERT INTO journal_entry_lines 
                (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                VALUES (?, 1, ?, ?, ?, 0)
            """, (je_id, cash_account, f"{description} - مدين", amount))
            
            counterpart = self._get_counterpart_account('DEPOSIT')
            cur.execute("""
                INSERT INTO journal_entry_lines 
                (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                VALUES (?, 2, ?, ?, 0, ?)
            """, (je_id, counterpart, f"{description} - دائن", amount))
        else:
            counterpart = self._get_counterpart_account('WITHDRAW')
            cur.execute("""
                INSERT INTO journal_entry_lines 
                (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                VALUES (?, 1, ?, ?, ?, 0)
            """, (je_id, counterpart, f"{description} - مدين", amount))
            
            cur.execute("""
                INSERT INTO journal_entry_lines 
                (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                VALUES (?, 2, ?, ?, 0, ?)
            """, (je_id, cash_account, f"{description} - دائن", amount))
        
        cur.execute("""
            UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
        """, (amount, amount, je_id))
        
        return je_id, je_no
    
    
    def _create_transfer_journal(self, conn, date, amount, from_account, to_account, ref_no, description):
        cur = conn.cursor()
        year = datetime.now().year
        
        cur.execute(
            "SELECT COUNT(*)+1 FROM journal_entries WHERE strftime('%Y', entry_date)=?",
            (str(year),)
        )
        n = cur.fetchone()[0]
        je_no = f"JE-{year}-{n:06d}"
        
        cur.execute("""
            INSERT INTO journal_entries 
            (entry_no, entry_date, reference_type, reference_no, description, status)
            VALUES (?, ?, 'CASH_BOX_TRANSFER', ?, ?, 'POSTED')
        """, (je_no, date, ref_no, description))
        je_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 1, ?, 'تحويل - مدين', ?, 0)
        """, (je_id, to_account, amount))
        
        cur.execute("""
            INSERT INTO journal_entry_lines 
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 2, ?, 'تحويل - دائن', 0, ?)
        """, (je_id, from_account, amount))
        
        cur.execute("""
            UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
        """, (amount, amount, je_id))
        
        return je_id, je_no
    
    
    def _get_counterpart_account(self, txn_type):
        """يرجع حساب مقابل من الإعدادات أو افتراضي"""
        try:
            acc = get_accounting()
            if txn_type == 'DEPOSIT':
                return acc.get('default_deposit_account', '3100')
            else:
                return acc.get('default_withdraw_account', '5200')
        except:
            return '3100' if txn_type == 'DEPOSIT' else '5200'


cash_box_service = CashBoxService()