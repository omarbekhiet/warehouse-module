from app.utils import round_decimal, to_decimal
from app.services.doc_number_service import doc_number_service


class AccountMappingError(Exception):
    pass


class AccountingService:

    def _get_mapping(self, conn, txn_type, item_type):
        cur = conn.execute(
            """SELECT debit_account, credit_account
               FROM inventory_account_mappings
               WHERE transaction_type=?
                 AND (item_type=? OR item_type IS NULL)
                 AND is_active=1
               ORDER BY item_type DESC LIMIT 1""",
            (txn_type, item_type)
        )
        row = cur.fetchone()
        if not row:
            raise AccountMappingError(f'لا يوجد ربط محاسبي للنوع: {txn_type}/{item_type}')
        return dict(row)

    def create_journal_entry(self, conn, transaction, lines):
        entry_no = doc_number_service.journal(conn)

        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id,
                reference_no, description, status)
               VALUES (?, ?, 'STOCK_TRANSACTION', ?, ?, ?, 'POSTED')""",
            (entry_no, transaction['transaction_date'], transaction['id'],
             transaction['transaction_no'],
             f"قيد مخزني - {transaction['transaction_no']}")
        )
        je_id = cur.lastrowid

        agg = {}
        for line in lines:
            m = self._get_mapping(conn, transaction['transaction_type'], line.get('item_type'))
            d, c = m['debit_account'], m['credit_account']
            cost = to_decimal(line['total_cost'])

            kd = d + '_D'
            if kd not in agg:
                agg[kd] = {'account': d, 'debit': 0, 'credit': 0}
            agg[kd]['debit'] += cost

            kc = c + '_C'
            if kc not in agg:
                agg[kc] = {'account': c, 'debit': 0, 'credit': 0}
            agg[kc]['credit'] += cost

        line_no = 1
        td = tc = 0
        for key in agg:
            item = agg[key]
            debit = round_decimal(item['debit'])
            credit = round_decimal(item['credit'])
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description,
                    debit_amount, credit_amount)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (je_id, line_no, item['account'],
                 f"قيد {transaction['transaction_no']}",
                 float(debit), float(credit))
            )
            td += float(debit)
            tc += float(credit)
            line_no += 1

        conn.execute(
            "UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
            (td, tc, je_id)
        )
        return je_id


accounting_service = AccountingService()
