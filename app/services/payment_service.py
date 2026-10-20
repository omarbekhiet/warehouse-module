from app.database import db
from app.services.settings_service import get_accounting
from app.utils import json_safe
from datetime import datetime


class PaymentService:
    """خدمة إدارة الدفعات والقبضات مع التوزيع على الفواتير"""

    # =========================================
    # Supplier Payments - مدفوعات الموردين
    # =========================================
    
    def create_supplier_payment(self, data, user_id=1):
        """إنشاء دفعة لمورد مع توزيعها على الفواتير"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            # 1. الحصول على طريقة السداد
            cur.execute(
                "SELECT account_code, requires_clearing FROM payment_methods WHERE code=?",
                (data['payment_method'],)
            )
            pm = cur.fetchone()
            if not pm:
                return {'success': False, 'message': 'طريقة سداد غير صحيحة'}
            
            cash_account = pm['account_code']
            requires_clearing = pm['requires_clearing']
            
            # 2. توليد رقم الدفعة
            year = datetime.now().year
            cur.execute("SELECT COUNT(*)+1 FROM supplier_payments")
            n = cur.fetchone()[0]
            payment_no = f"PAY-{year}-{n:06d}"
            
            # 3. إنشاء الدفعة
            cur.execute("""
                INSERT INTO supplier_payments
                (payment_no, payment_date, supplier_id, payment_method,
                 amount, reference, notes, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'POSTED', ?)
            """, (
                payment_no, data['payment_date'], data['supplier_id'],
                data['payment_method'], float(data['amount']),
                data.get('reference'), data.get('notes'), user_id
            ))
            payment_id = cur.lastrowid
            # ✅ حفظ السطور المتعددة
            lines = data.get('lines', [])
            if lines:
                for idx, line in enumerate(lines, 1):
                    cur.execute("""
                        INSERT INTO payment_lines 
                        (parent_type, parent_id, line_no, line_type,
                         account_code, account_name, amount, direction,
                         tax_rate, tax_base, discount_type, discount_rate,
                         description, reference)
                        VALUES ('SUPPLIER_PAYMENT', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        payment_id, idx, line.get('line_type', 'MAIN'),
                        line['account_code'], line.get('account_name'),
                        float(line['amount']), line.get('direction', 'DEBIT'),
                        float(line.get('tax_rate', 0) or 0),
                        float(line.get('tax_base', 0) or 0),
                        line.get('discount_type'),
                        float(line.get('discount_rate', 0) or 0),
                        line.get('description'), line.get('reference')
                    ))
            
            # ✅ تسجيل حركة الخزينة (دفع)
            cash_box_id = data.get('cash_box_id')
            cash_box_type = data.get('cash_box_type', 'CASH_BOX')
            
            if cash_box_id:
                table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
                box_table = table_map.get(cash_box_type, 'cash_boxes')
                
                cur.execute(f"SELECT * FROM {box_table} WHERE id=?", (cash_box_id,))
                box = cur.fetchone()
                
                if box:
                    current_bal = float(box['current_balance'] or 0)
                    new_bal = current_bal - float(data['amount'])
                    
                    cur.execute(f"UPDATE {box_table} SET current_balance=? WHERE id=?", (new_bal, cash_box_id))
                    
                    cur.execute("""
                        INSERT INTO cash_box_transactions 
                        (box_id, box_type, txn_type, txn_date, amount, balance_after,
                         reference_no, description, created_by)
                        VALUES (?, ?, 'WITHDRAW', ?, ?, ?, ?, ?, ?)
                    """, (
                        cash_box_id, cash_box_type, data['payment_date'],
                        float(data['amount']), new_bal, payment_no,
                        f"دفعة لمورد - {payment_no}", user_id
                    ))
            
            # فحص القيد التلقائي
            acc_settings = get_accounting()
            auto_journal = acc_settings.get('auto_journal_receipts', True)
            
            if auto_journal:
                # 4. القيد المحاسبي
                je_no = self._next_journal_no(conn)
                cur.execute("""
                    INSERT INTO journal_entries
                    (entry_no, entry_date, reference_type, reference_id, 
                     reference_no, description, status)
                    VALUES (?, ?, 'SUPPLIER_PAYMENT', ?, ?, ?, 'POSTED')
                """, (
                    je_no, data['payment_date'], payment_id, payment_no,
                    f"سداد مورد - {payment_no}"
                ))
                je_id = cur.lastrowid
            
                # Debit: AP (2211)
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, 
                     debit_amount, credit_amount)
                    VALUES (?, 1, '2211', 'ذمم الموردين - سداد', ?, 0)
                """, (je_id, float(data['amount'])))
            
                # Credit: Cash account
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description,
                     debit_amount, credit_amount)
                    VALUES (?, 2, ?, 'نقدية - سداد مورد', 0, ?)
                """, (je_id, cash_account, float(data['amount'])))
            
                # تحديث القيد
                cur.execute("""
                    UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
                """, (float(data['amount']), float(data['amount']), je_id))
            else:
                je_id = None
                je_no = None
            
            # 5. التوزيع على الفواتير (Allocations)
            allocations = data.get('allocations', [])
            total_allocated = 0
            
            for alloc in allocations:
                amount = float(alloc['amount'])
                if amount <= 0:
                    continue
                
                # الحصول على رقم الفاتورة
                cur.execute(
                    "SELECT invoice_no, total_amount FROM purchase_invoices WHERE id=?",
                    (alloc['invoice_id'],)
                )
                inv = cur.fetchone()
                if not inv:
                    continue
                
                # التحقق من عدم تجاوز المبلغ الإجمالي
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM payment_allocations
                    WHERE payment_type='SUPPLIER_PAYMENT' 
                      AND invoice_id=? AND invoice_type='PURCHASE'
                """, (alloc['invoice_id'],))
                already_paid = float(cur.fetchone()[0])
                
                remaining = float(inv['total_amount']) - already_paid
                if amount > remaining:
                    amount = remaining
                
                if amount <= 0:
                    continue
                
                cur.execute("""
                    INSERT INTO payment_allocations
                    (payment_id, payment_type, invoice_id, invoice_type,
                     invoice_no, amount)
                    VALUES (?, 'SUPPLIER_PAYMENT', ?, 'PURCHASE', ?, ?)
                """, (payment_id, alloc['invoice_id'], inv['invoice_no'], amount))
                
                total_allocated += amount
            
            # 6. تسجيل القيد للدفعة
            cur.execute(
                "UPDATE supplier_payments SET journal_entry_id=? WHERE id=?",
                (je_id, payment_id)
            )
            
            conn.commit()
            
            return {
                'success': True,
                'data': {
                    'id': payment_id,
                    'payment_no': payment_no,
                    'amount': float(data['amount']),
                    'allocated': total_allocated,
                    'journal_entry_id': je_id,
                    'journal_entry_no': je_no
                }
            }
    
    
    def get_supplier_open_invoices(self, supplier_id):
        """الفواتير المفتوحة (غير المسددة) للمورد"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    pi.id,
                    pi.invoice_no,
                    pi.invoice_date,
                    pi.total_amount,
                    pi.payment_type,
                    pi.status,
                    COALESCE(pa.paid, 0) as paid_amount,
                    pi.total_amount - COALESCE(pa.paid, 0) as remaining
                FROM purchase_invoices pi
                LEFT JOIN (
                    SELECT invoice_id, SUM(amount) as paid
                    FROM payment_allocations
                    WHERE payment_type='SUPPLIER_PAYMENT' AND invoice_type='PURCHASE'
                    GROUP BY invoice_id
                ) pa ON pi.id = pa.invoice_id
                WHERE pi.supplier_id = ?
                  AND pi.status = 'POSTED'
                  AND pi.payment_type = 'CREDIT'
                  AND pi.total_amount > COALESCE(pa.paid, 0)
                ORDER BY pi.invoice_date
            """, (supplier_id,))
            
            return [dict(r) for r in cur.fetchall()]
    
    
    # =========================================
    # Customer Receipts - تحصيلات العملاء
    # =========================================
    
    def create_customer_receipt(self, data, user_id=1):
        """إنشاء تحصيل من عميل مع توزيعه على الفواتير"""
        with db.transaction() as conn:
            cur = conn.cursor()
            
            # 1. طريقة الاستلام
            cur.execute(
                "SELECT account_code, requires_clearing FROM payment_methods WHERE code=?",
                (data['receipt_method'],)
            )
            pm = cur.fetchone()
            if not pm:
                return {'success': False, 'message': 'طريقة استلام غير صحيحة'}
            
            cash_account = pm['account_code']
            
            # 2. رقم الإيصال
            year = datetime.now().year
            cur.execute("SELECT COUNT(*)+1 FROM customer_receipts")
            n = cur.fetchone()[0]
            receipt_no = f"RCP-{year}-{n:06d}"
            
            # 3. إنشاء الإيصال
            cur.execute("""
                INSERT INTO customer_receipts
                (receipt_no, receipt_date, customer_id, receipt_method,
                 amount, reference, notes, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'POSTED', ?)
            """, (
                receipt_no, data['receipt_date'], data['customer_id'],
                data['receipt_method'], float(data['amount']),
                data.get('reference'), data.get('notes'), user_id
            ))
            receipt_id = cur.lastrowid
            # ✅ حفظ السطور المتعددة
            lines = data.get('lines', [])
            if lines:
                for idx, line in enumerate(lines, 1):
                    cur.execute("""
                        INSERT INTO payment_lines 
                        (parent_type, parent_id, line_no, line_type,
                         account_code, account_name, amount, direction,
                         tax_rate, tax_base, discount_type, discount_rate,
                         description, reference)
                        VALUES ('CUSTOMER_RECEIPT', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        receipt_id, idx, line.get('line_type', 'MAIN'),
                        line['account_code'], line.get('account_name'),
                        float(line['amount']), line.get('direction', 'DEBIT'),
                        float(line.get('tax_rate', 0) or 0),
                        float(line.get('tax_base', 0) or 0),
                        line.get('discount_type'),
                        float(line.get('discount_rate', 0) or 0),
                        line.get('description'), line.get('reference')
                    ))

            
            
            # ✅ تسجيل حركة الخزينة (تحصيل)
            cash_box_id = data.get('cash_box_id')
            cash_box_type = data.get('cash_box_type', 'CASH_BOX')
            
            if cash_box_id:
                table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
                box_table = table_map.get(cash_box_type, 'cash_boxes')
                
                cur.execute(f"SELECT * FROM {box_table} WHERE id=?", (cash_box_id,))
                box = cur.fetchone()
                
                if box:
                    current_bal = float(box['current_balance'] or 0)
                    new_bal = current_bal + float(data['amount'])
                    
                    cur.execute(f"UPDATE {box_table} SET current_balance=? WHERE id=?", (new_bal, cash_box_id))
                    
                    cur.execute("""
                        INSERT INTO cash_box_transactions 
                        (box_id, box_type, txn_type, txn_date, amount, balance_after,
                         reference_no, description, created_by)
                        VALUES (?, ?, 'DEPOSIT', ?, ?, ?, ?, ?, ?)
                    """, (
                        cash_box_id, cash_box_type, data['receipt_date'],
                        float(data['amount']), new_bal, receipt_no,
                        f"تحصيل من عميل - {receipt_no}", user_id
                    ))
            # 4. القيد (فحص auto_journal_receipts)
            acc_settings = get_accounting()
            auto_journal = acc_settings.get('auto_journal_receipts', True)

            if auto_journal:
                je_no = self._next_journal_no(conn)
                cur.execute("""
                    INSERT INTO journal_entries
                    (entry_no, entry_date, reference_type, reference_id,
                     reference_no, description, status)
                    VALUES (?, ?, 'CUSTOMER_RECEIPT', ?, ?, ?, 'POSTED')
                """, (
                    je_no, data['receipt_date'], receipt_id, receipt_no,
                    f"تحصيل من عميل - {receipt_no}"
                ))
                je_id = cur.lastrowid
                # Debit: Cash
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description,
                     debit_amount, credit_amount)
                    VALUES (?, 1, ?, 'نقدية - تحصيل', ?, 0)
                """, (je_id, cash_account, float(data['amount'])))
            
                # Credit: AR (1221)
                cur.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description,
                     debit_amount, credit_amount)
                    VALUES (?, 2, '1221', 'ذمم العملاء - تحصيل', 0, ?)
                """, (je_id, float(data['amount'])))
            
                cur.execute("""
                    UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?
                """, (float(data['amount']), float(data['amount']), je_id))
            else:
                je_id = None
                je_no = None
            
            # 5. التوزيع
            allocations = data.get('allocations', [])
            total_allocated = 0
            
            for alloc in allocations:
                amount = float(alloc['amount'])
                if amount <= 0:
                    continue
                
                cur.execute(
                    "SELECT invoice_no, total_amount FROM sales_invoices WHERE id=?",
                    (alloc['invoice_id'],)
                )
                inv = cur.fetchone()
                if not inv:
                    continue
                
                cur.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM payment_allocations
                    WHERE payment_type='CUSTOMER_RECEIPT'
                      AND invoice_id=? AND invoice_type='SALES'
                """, (alloc['invoice_id'],))
                already_paid = float(cur.fetchone()[0])
                
                remaining = float(inv['total_amount']) - already_paid
                if amount > remaining:
                    amount = remaining
                
                if amount <= 0:
                    continue
                
                cur.execute("""
                    INSERT INTO payment_allocations
                    (payment_id, payment_type, invoice_id, invoice_type,
                     invoice_no, amount)
                    VALUES (?, 'CUSTOMER_RECEIPT', ?, 'SALES', ?, ?)
                """, (receipt_id, alloc['invoice_id'], inv['invoice_no'], amount))
                
                total_allocated += amount
            
            cur.execute(
                "UPDATE customer_receipts SET journal_entry_id=? WHERE id=?",
                (je_id, receipt_id)
            )
            
            conn.commit()
            
            return {
                'success': True,
                'data': {
                    'id': receipt_id,
                    'receipt_no': receipt_no,
                    'amount': float(data['amount']),
                    'allocated': total_allocated,
                    'journal_entry_id': je_id,
                    'journal_entry_no': je_no
                }
            }
    
    
    def get_customer_open_invoices(self, customer_id):
        """الفواتير المفتوحة (غير المحصلة) للعميل"""
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    si.id,
                    si.invoice_no,
                    si.invoice_date,
                    si.total_amount,
                    si.payment_type,
                    si.status,
                    COALESCE(pa.paid, 0) as paid_amount,
                    si.total_amount - COALESCE(pa.paid, 0) as remaining
                FROM sales_invoices si
                LEFT JOIN (
                    SELECT invoice_id, SUM(amount) as paid
                    FROM payment_allocations
                    WHERE payment_type='CUSTOMER_RECEIPT' AND invoice_type='SALES'
                    GROUP BY invoice_id
                ) pa ON si.id = pa.invoice_id
                WHERE si.customer_id = ?
                  AND si.status = 'POSTED'
                  AND si.payment_type = 'CREDIT'
                  AND si.total_amount > COALESCE(pa.paid, 0)
                ORDER BY si.invoice_date
            """, (customer_id,))
            
            return [dict(r) for r in cur.fetchall()]
    
    
    # =========================================
    # Helpers
    # =========================================
    
    def _next_journal_no(self, conn):
        year = datetime.now().year
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*)+1 FROM journal_entries WHERE strftime('%Y', created_at)=?",
            (str(year),)
        )
        n = cur.fetchone()[0]
        return f"JE-{year}-{n:06d}"


payment_service = PaymentService()