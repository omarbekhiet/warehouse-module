"""
خدمة القيود المحاسبية — نسخة مطوّرة
تدعم stock_movements + WAREHOUSE placeholders + الضريبة
"""
from app.utils import round_decimal, to_decimal
from app.services.doc_number_service import doc_number_service


class AccountMappingError(Exception):
    pass


class AccountingService:

    # ============================================================
    # استبدال الحسابات المتغيرة
    # ============================================================
    def _resolve_side(self, side, warehouse, warehouse_from=None, warehouse_to=None):
        if not side:
            return None
        if side == 'WAREHOUSE':
            return self._get_warehouse_account(warehouse)
        if side == 'WAREHOUSE_TO':
            return self._get_warehouse_account(warehouse_to)
        if side == 'WAREHOUSE_FROM':
            return self._get_warehouse_account(warehouse_from)
        return side

    def _get_warehouse_account(self, warehouse):
        if not warehouse:
            return None
        if isinstance(warehouse, dict):
            return warehouse.get('account_code')
        if isinstance(warehouse, int):
            w = self._query_warehouse(warehouse)
            return w.get('account_code') if w else None
        return None

    def _query_warehouse(self, warehouse_id):
        from app.database import db
        r = db.query(
            "SELECT id, code, name_ar, account_code FROM warehouses WHERE id=?",
            (warehouse_id,), one=True
        )
        return dict(r) if r else None

    # ============================================================
    # توليد القيد
    # ============================================================
    def create_journal_entry(self, conn, transaction, lines, 
                             tax_amount=0, extra_amount=0):
        movement_code = transaction.get('movement_code') or \
                        self._infer_movement_code(transaction['transaction_type'])
        if not movement_code:
            raise AccountMappingError(
                f'لا يمكن تحديد نوع الحركة: {transaction["transaction_type"]}'
            )
        
        movement = self._get_movement(conn, movement_code)
        if not movement:
            raise AccountMappingError(f'نوع الحركة {movement_code} غير موجود')
        
        # جيب المستودعات
        warehouse = warehouse_from = warehouse_to = None
        primary_wh_id = transaction.get('to_warehouse_id') or transaction.get('from_warehouse_id')
        if primary_wh_id:
            warehouse = self._query_warehouse(primary_wh_id)
        
        if transaction.get('from_warehouse_id') and transaction.get('to_warehouse_id'):
            warehouse_from = self._query_warehouse(transaction['from_warehouse_id'])
            warehouse_to = self._query_warehouse(transaction['to_warehouse_id'])
        
        # استبدل الحسابات
        debit_acc = self._resolve_side(movement['debit_side'], warehouse, warehouse_from, warehouse_to)
        credit_acc = self._resolve_side(movement['credit_side'], warehouse, warehouse_from, warehouse_to)
        tax_acc = self._resolve_side(movement['tax_side'], warehouse, warehouse_from, warehouse_to) if movement.get('tax_side') else None
        extra_acc = self._resolve_side(movement['extra_side'], warehouse, warehouse_from, warehouse_to) if movement.get('extra_side') else None
        
        if not debit_acc or not credit_acc:
            raise AccountMappingError(
                f'لا يمكن تحديد الحسابات: debit={debit_acc}, credit={credit_acc} (movement={movement_code})'
            )
        
        # احسب الإجماليات
        total_amount = round_decimal(to_decimal(sum(float(l.get('total_cost', 0)) for l in lines)))
        tax_amount = round_decimal(to_decimal(tax_amount)) if tax_amount else 0
        extra_amount = round_decimal(to_decimal(extra_amount)) if extra_amount else 0
        
        # رأس القيد
        entry_no = doc_number_service.journal(conn)
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id,
                reference_no, description, status)
               VALUES (?, ?, ?, ?, ?, ?, 'POSTED')""",
            (entry_no, transaction['transaction_date'],
             transaction.get('reference_type', 'STOCK_TRANSACTION'),
             transaction['id'],
             transaction['transaction_no'],
             f"{movement['name_ar']} - {transaction['transaction_no']}")
        )
        je_id = cur.lastrowid
        
        # سطور القيد
        line_no = 1
        total_debit = 0
        total_credit = 0
        wh_id = warehouse.get('id') if warehouse else None
        
        # المدين الأساسي
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description,
                debit_amount, credit_amount, warehouse_id)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (je_id, line_no, debit_acc,
             f"{movement['name_ar']} - {transaction['transaction_no']}",
             float(total_amount), wh_id)
        )
        total_debit += float(total_amount)
        line_no += 1
        
        # الضريبة (مدين)
        if tax_acc and tax_amount > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description,
                    debit_amount, credit_amount, warehouse_id)
                   VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (je_id, line_no, tax_acc,
                 f"ضريبة - {transaction['transaction_no']}",
                 float(tax_amount), wh_id)
            )
            total_debit += float(tax_amount)
            line_no += 1
        
        # إضافي (دائن)
        if extra_acc and extra_amount > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description,
                    debit_amount, credit_amount, warehouse_id)
                   VALUES (?, ?, ?, ?, 0, ?, ?)""",
                (je_id, line_no, extra_acc,
                 f"إضافي - {transaction['transaction_no']}",
                 float(extra_amount), wh_id)
            )
            total_credit += float(extra_amount)
            line_no += 1
        
        # الدائن الأساسي
        credit_total = float(total_amount) + float(tax_amount) - float(extra_amount)
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description,
                debit_amount, credit_amount, warehouse_id)
               VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (je_id, line_no, credit_acc,
             f"{movement['name_ar']} - {transaction['transaction_no']}",
             credit_total, wh_id)
        )
        total_credit += credit_total
        
        # تحديث الإجماليات
        conn.execute(
            "UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
            (total_debit, total_credit, je_id)
        )
        
        return je_id

    def _get_movement(self, conn, movement_code):
        cur = conn.execute(
            "SELECT * FROM stock_movements WHERE code=? AND is_active=1",
            (movement_code,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _infer_movement_code(self, txn_type):
        mapping = {
            'RECEIPT': 'RECV',
            'ISSUE': 'ISSUE',
            'TRANSFER': 'TRANS',
            'ADJUSTMENT': 'ADJ+',
            'COUNT': 'ADJ+',
            'WASTE': 'WASTE',
            'PURCHASE_RETURN': 'PRET',
            'SALES_RETURN': 'SRET',
            'PURCHASE_INVOICE': 'PINV',
            'PURCHASE_INVOICE_RETURN': 'PRET_INV',
        }
        return mapping.get(txn_type)


accounting_service = AccountingService()