from app.database import db
from app.utils import json_safe
from datetime import datetime


class SettlementService:
    """خدمة تسوية الشيكات والبطاقات"""
    
    def _next_no(self, conn, table, prefix):
        year = datetime.now().year
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*)+1 FROM {table}")
        n = cur.fetchone()[0]
        return f"{prefix}-{year}-{n:06d}"
    
    def _next_journal_no(self, conn):
        year = datetime.now().year
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*)+1 FROM journal_entries WHERE strftime('%Y', created_at)=?",
            (str(year),)
        )
        return f"JE-{year}-{cur.fetchone()[0]:06d}"
    
    # =========================================
    # Cheque Settlements - تسوية الشيكات
    # =========================================
    
    def create_cheque_settlement(self, data, user_id=1):
        """تسوية شيك (تحصيل أو صرف)"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            no = self._next_no(conn, 'cheque_settlements', 'CHQ')
            
            cur.execute("""
                INSERT INTO cheque_settlements
                (settlement_no, settlement_date, settlement_type,
                 source_type, source_id, cheque_no, cheque_date,
                 bank_name, amount, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                no, data['settlement_date'], data['settlement_type'],
                data['source_type'], data['source_id'],
                data.get('cheque_no'), data.get('cheque_date'),
                data.get('bank_name'), float(data['amount']),
                data.get('notes')
            ))
            sid = cur.lastrowid
            
            conn.commit()
            
            return {
                'success': True,
                'data': {
                    'id': sid,
                    'settlement_no': no,
                    'status': 'PENDING'
                }
            }
    
    def clear_cheque(self, cheque_id, cleared_date=None, notes=None, user_id=1):
        """تحصيل شيك - تحويل من 1225 إلى البنك"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM cheque_settlements WHERE id=? AND status='PENDING'", (cheque_id,))
            chq = cur.fetchone()
            if not chq:
                return {'success': False, 'message': 'الشيك غير موجود أو تمت تسويته'}
            
            cleared_date = cleared_date or datetime.now().strftime('%Y-%m-%d')
            amount = float(chq['amount'])
            
            # القيد: مدين البنك / دائن شيكات تحت التحصيل
            je_no = self._next_journal_no(conn)
            cur.execute("""
                INSERT INTO journal_entries
                (entry_no, entry_date, reference_type, reference_id,
                 reference_no, description, status)
                VALUES (?, ?, 'CHEQUE_CLEARED', ?, ?, ?, 'POSTED')
            """, (
                je_no, cleared_date, cheque_id, chq['settlement_no'],
                f"تحصيل شيك - {chq['cheque_no'] or chq['settlement_no']}"
            ))
            je_id = cur.lastrowid
            
            # Debit: Bank
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, 1, '1212', 'البنك - تحصيل شيك', ?, 0)
            """, (je_id, amount))
            
            # Credit: Cheques under collection
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, 2, '1225', 'شيكات تحت التحصيل', 0, ?)
            """, (je_id, amount))
            
            cur.execute("""
                UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
            """, (amount, amount, je_id))
            
            # تحديث الشيك
            cur.execute("""
                UPDATE cheque_settlements
                SET status='CLEARED', cleared_date=?, journal_entry_id=?, notes=?
                WHERE id=?
            """, (cleared_date, je_id, notes, cheque_id))
            
            conn.commit()
            
            return {
                'success': True,
                'message': 'تم تحصيل الشيك',
                'data': {'journal_entry_id': je_id, 'journal_entry_no': je_no}
            }
    
    def bounce_cheque(self, cheque_id, bounce_date=None, reason=None, user_id=1):
        """ارتداد شيك - عكس القيد الأصلي"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM cheque_settlements WHERE id=? AND status='PENDING'", (cheque_id,))
            chq = cur.fetchone()
            if not chq:
                return {'success': False, 'message': 'الشيك غير موجود أو تمت تسويته'}
            
            bounce_date = bounce_date or datetime.now().strftime('%Y-%m-%d')
            amount = float(chq['amount'])
            
            # القيد العكسي: مدين شيكات تحت التحصيل / دائن البنك
            # (لأن الشيك لم يُحصّل - يجب إعادة الذمة للمورد/العميل)
            je_no = self._next_journal_no(conn)
            cur.execute("""
                INSERT INTO journal_entries
                (entry_no, entry_date, reference_type, reference_id,
                 reference_no, description, status)
                VALUES (?, ?, 'CHEQUE_BOUNCED', ?, ?, ?, 'POSTED')
            """, (
                je_no, bounce_date, cheque_id, chq['settlement_no'],
                f"ارتداد شيك - {chq['cheque_no'] or chq['settlement_no']}"
            ))
            je_id = cur.lastrowid
            
            # Debit: Cheques under collection (إعادة)
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, 1, '1225', 'شيكات تحت التحصيل - ارتداد', ?, 0)
            """, (je_id, amount))
            
            # Credit: Bank
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, 2, '1212', 'البنك - ارتداد شيك', 0, ?)
            """, (je_id, amount))
            
            cur.execute("""
                UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
            """, (amount, amount, je_id))
            
            cur.execute("""
                UPDATE cheque_settlements
                SET status='BOUNCED', cleared_date=?, journal_entry_id=?, notes=?
                WHERE id=?
            """, (bounce_date, je_id, f"ارتداد: {reason or 'بدون سبب'}", cheque_id))
            
            # إذا كان شيك صادر لمورد، إعادة ذمته
            if chq['source_type'] == 'SUPPLIER_PAYMENT':
                # إعادة الذمة للعميل/المورد
                # (سنفعل ذلك عبر قيد إضافي أو تعديل payment_allocations)
                pass
            
            conn.commit()
            
            return {
                'success': True,
                'message': 'تم تسجيل ارتداد الشيك',
                'data': {'journal_entry_id': je_id, 'journal_entry_no': je_no}
            }
    
    # =========================================
    # Card Settlements - تسوية البطاقات
    # =========================================
    
    def create_card_settlement(self, data, user_id=1):
        """تسوية بطاقة مع حساب العمولة"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            no = self._next_no(conn, 'card_settlements', 'CRD')
            
            gross = float(data['gross_amount'])
            comm_pct = float(data.get('commission_pct', 0))
            comm_amount = gross * comm_pct / 100
            net = gross - comm_amount
            
            cur.execute("""
                INSERT INTO card_settlements
                (settlement_no, settlement_date, source_type, source_id,
                 card_type, transaction_no, gross_amount, commission_pct,
                 commission_amount, net_amount, bank_account, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                no, data['settlement_date'], data['source_type'], data['source_id'],
                data.get('card_type'), data.get('transaction_no'),
                gross, comm_pct, comm_amount, net, 
                data.get('bank_account', '1212'), data.get('notes')
            ))
            sid = cur.lastrowid
            
            # القيد: مدين البنك + عمولة / دائن بطاقات وسيطة
            je_no = self._next_journal_no(conn)
            cur.execute("""
                INSERT INTO journal_entries
                (entry_no, entry_date, reference_type, reference_id,
                 reference_no, description, status)
                VALUES (?, ?, 'CARD_SETTLEMENT', ?, ?, ?, 'POSTED')
            """, (
                je_no, data['settlement_date'], sid, no,
                f"تسوية بطاقة - {no}"
            ))
            je_id = cur.lastrowid
            
            line_no = 1
            
            # Debit: Bank (net)
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, ?, '1212', 'البنك - تسوية بطاقة', ?, 0)
            """, (je_id, line_no, net))
            line_no += 1
            
            # Debit: Commission expense
            if comm_amount > 0:
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description,
                     debit_amount, credit_amount)
                    VALUES (?, ?, '6210', 'عمولة بطاقة', ?, 0)
                """, (je_id, line_no, comm_amount))
                line_no += 1
            
            # Credit: Card clearing (gross)
            cur.execute("""
                INSERT INTO journal_entry_lines
                (journal_entry_id, line_no, account_code, description,
                 debit_amount, credit_amount)
                VALUES (?, ?, '1213', 'بطاقات وسيطة', 0, ?)
            """, (je_id, line_no, gross))
            
            cur.execute("""
                UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
            """, (net + comm_amount, gross, je_id))
            
            # تحديث التسوية
            cur.execute("""
                UPDATE card_settlements
                SET status='CLEARED', settled_date=?, journal_entry_id=?
                WHERE id=?
            """, (data['settlement_date'], je_id, sid))
            
            conn.commit()
            
            return {
                'success': True,
                'data': {
                    'id': sid,
                    'settlement_no': no,
                    'gross': gross,
                    'commission': comm_amount,
                    'net': net,
                    'journal_entry_no': je_no
                }
            }
    
    # =========================================
    # Queries
    # =========================================
    
    def list_pending_cheques(self, direction=None):
        """قائمة الشيكات المعلقة"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            sql = """
                SELECT cs.*,
                       CASE 
                         WHEN cs.source_type='SUPPLIER_PAYMENT' THEN 
                            (SELECT s.name_ar FROM supplier_payments sp 
                             LEFT JOIN suppliers s ON sp.supplier_id=s.id 
                             WHERE sp.id=cs.source_id)
                         WHEN cs.source_type='CUSTOMER_RECEIPT' THEN
                            (SELECT c.name_ar FROM customer_receipts cr
                             LEFT JOIN customers c ON cr.customer_id=c.id
                             WHERE cr.id=cs.source_id)
                       END as party_name
                FROM cheque_settlements cs
                WHERE cs.status='PENDING'
            """
            
            if direction:
                sql += " AND cs.settlement_type=?"
                cur.execute(sql + " ORDER BY cs.settlement_date", (direction,))
            else:
                cur.execute(sql + " ORDER BY cs.settlement_date")
            
            return [dict(r) for r in cur.fetchall()]
    
    def list_pending_cards(self):
        """قائمة البطاقات المعلقة"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT cs.*,
                       CASE 
                         WHEN cs.source_type='SUPPLIER_PAYMENT' THEN 
                            (SELECT s.name_ar FROM supplier_payments sp 
                             LEFT JOIN suppliers s ON sp.supplier_id=s.id 
                             WHERE sp.id=cs.source_id)
                         WHEN cs.source_type='CUSTOMER_RECEIPT' THEN
                            (SELECT c.name_ar FROM customer_receipts cr
                             LEFT JOIN customers c ON cr.customer_id=c.id
                             WHERE cr.id=cs.source_id)
                       END as party_name
                FROM card_settlements cs
                WHERE cs.status='PENDING'
                ORDER BY cs.settlement_date
            """)
            return [dict(r) for r in cur.fetchall()]
    
    def list_cheque_settlements(self, status=None):
        """قائمة كل تسويات الشيكات"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            sql = "SELECT * FROM cheque_settlements"
            params = []
            if status:
                sql += " WHERE status=?"
                params.append(status)
            sql += " ORDER BY id DESC LIMIT 200"
            
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    
    def list_card_settlements(self):
        """قائمة كل تسويات البطاقات"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM card_settlements ORDER BY id DESC LIMIT 200")
            return [dict(r) for r in cur.fetchall()]


settlement_service = SettlementService()