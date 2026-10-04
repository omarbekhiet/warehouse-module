from datetime import datetime
from app.config import Config


class DocNumberService:
    def _next(self, conn, prefix, txn_type):
        year = datetime.now().year
        cur = conn.execute(
            """SELECT COUNT(*) AS n FROM stock_transactions
               WHERE transaction_type=? AND strftime('%Y', created_at)=?""",
            (txn_type, str(year))
        )
        n = cur.fetchone()['n'] + 1
        return f'{prefix}-{year}-{n:06d}'

    def receipt(self, conn): return self._next(conn, 'REC', 'RECEIPT')
    def issue(self, conn): return self._next(conn, 'ISS', 'ISSUE')
    def transfer(self, conn): return self._next(conn, 'TRF', 'TRANSFER')
    def count(self, conn): return self._next(conn, 'CNT', 'COUNT_ADJUST')
    def adjust(self, conn): return self._next(conn, 'ADJ', 'COUNT_ADJUST')

    def journal(self, conn):
        year = datetime.now().year
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM journal_entries WHERE strftime('%Y', created_at)=?",
            (str(year),)
        )
        n = cur.fetchone()['n'] + 1
        return f'JE-{year}-{n:06d}'


doc_number_service = DocNumberService()
