from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

count_bp = Blueprint('counts', __name__)


def _next_count_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM inventory_counts")
    n = cur.fetchone()['n']
    return f"CNT-{datetime.now().year}-{n:06d}"


@count_bp.route('/', methods=['GET'])
def list_counts():
    rows = db.query(
        """SELECT ic.*, w.name_ar as warehouse_name
           FROM inventory_counts ic
           LEFT JOIN warehouses w ON ic.warehouse_id = w.id
           ORDER BY ic.id DESC LIMIT 100"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@count_bp.route('/<int:cid>', methods=['GET'])
def get_count(cid):
    row = db.query("SELECT * FROM inventory_counts WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, i.name_ar as item_name, i.code as item_code,
                  (l.counted_qty - l.system_qty) as variance_qty
           FROM inventory_count_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.count_id=?""",
        (cid,)
    )
    row['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(row)})


@count_bp.route('/', methods=['POST'])
def create_count():
    d = request.get_json() or {}
    if not d.get('warehouse_id'):
        return jsonify({'success': False, 'message': 'warehouse_id مطلوب'}), 400
    with db.transaction() as conn:
        count_no = _next_count_no(conn)
        cur = conn.execute(
            """INSERT INTO inventory_counts
               (count_no, warehouse_id, count_date, count_type, status)
               VALUES (?, ?, ?, ?, 'DRAFT')""",
            (count_no, d['warehouse_id'],
             d.get('count_date', datetime.now().strftime('%Y-%m-%d')),
             d.get('count_type', 'FULL'))
        )
        cid = cur.lastrowid
        cur = conn.execute(
            "SELECT item_id, batch_no, quantity, average_cost FROM stock_balances WHERE warehouse_id=? AND quantity > 0",
            (d['warehouse_id'],)
        )
        for bal in cur.fetchall():
            conn.execute(
                """INSERT INTO inventory_count_lines
                   (count_id, item_id, system_qty, counted_qty, unit_cost)
                   VALUES (?, ?, ?, ?, ?)""",
                (cid, bal['item_id'], bal['quantity'], bal['quantity'], bal['average_cost'] or 0)
            )
    return jsonify({'success': True, 'data': {'id': cid, 'count_no': count_no}}), 201


@count_bp.route('/<int:cid>/count', methods=['PUT'])
def update_counted(cid):
    d = request.get_json() or {}
    lines = d.get('lines', [])
    if not lines:
        return jsonify({'success': False, 'message': 'لا توجد بنود'}), 400
    with db.transaction() as conn:
        for l in lines:
            conn.execute(
                """UPDATE inventory_count_lines 
                   SET counted_qty=?, variance_value=(? - system_qty) * unit_cost
                   WHERE id=? AND count_id=?""",
                (l['counted_qty'], l['counted_qty'], l['id'], cid)
            )
        conn.execute("UPDATE inventory_counts SET status='IN_PROGRESS' WHERE id=?", (cid,))
    return jsonify({'success': True, 'message': 'تم التحديث'})


@count_bp.route('/<int:cid>/post', methods=['POST'])
def post_count(cid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM inventory_counts WHERE id=? AND status IN ('DRAFT','IN_PROGRESS')", (cid,))
        count = cur.fetchone()
        if not count:
            return jsonify({'success': False, 'message': 'الجرد غير موجود أو مرحّل'}), 404
        count = dict(count)

        cur = conn.execute(
            """SELECT l.*, i.name_ar, i.item_type
               FROM inventory_count_lines l
               JOIN items i ON l.item_id = i.id
               WHERE l.count_id=? AND (l.counted_qty - l.system_qty) != 0""",
            (cid,)
        )
        lines = [dict(r) for r in cur.fetchall()]
        if not lines:
            return jsonify({'success': False, 'message': 'لا توجد فروق للتسوية'}), 400

        cur = conn.execute("SELECT COUNT(*)+1 as n FROM stock_transactions WHERE transaction_type='COUNT_ADJUST'")
        n = cur.fetchone()['n']
        txn_no = f"ADJ-{datetime.now().year}-{n:06d}"

        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, from_warehouse_id, reference_type,
                reference_id, reference_no, status, notes, created_by)
               VALUES (?, 'COUNT_ADJUST', ?, ?, ?, 'INVENTORY_COUNT', ?, ?, 'DRAFT', ?, 1)""",
            (txn_no, count['count_date'], count['warehouse_id'], count['warehouse_id'],
             count['id'], count['count_no'], f"تسوية جرد {count['count_no']}")
        )
        txn_id = cur.lastrowid

        adj_lines = []
        for i, line in enumerate(lines, start=1):
            variance = float(line['counted_qty']) - float(line['system_qty'])
            unit_cost = float(line['unit_cost']) or 0
            variance_value = variance * unit_cost
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, 1, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], variance, unit_cost, variance_value)
            )
            conn.execute(
                """UPDATE stock_balances
                   SET quantity = quantity + ?, total_value = total_value + ?
                   WHERE warehouse_id=? AND item_id=?""",
                (variance, variance_value, count['warehouse_id'], line['item_id'])
            )
            adj_lines.append({'item_id': line['item_id'], 'item_type': line['item_type'], 'total_cost': variance_value})

        conn.execute(
            """UPDATE stock_transactions SET
                 total_qty = (SELECT COALESCE(SUM(quantity),0) FROM stock_transaction_lines WHERE transaction_id=?),
                 total_value = (SELECT COALESCE(SUM(total_cost),0) FROM stock_transaction_lines WHERE transaction_id=?)
               WHERE id=?""",
            (txn_id, txn_id, txn_id)
        )

        entry_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
               VALUES (?, ?, 'INVENTORY_COUNT', ?, ?, ?, 'POSTED')""",
            (entry_no, count['count_date'], cid, count['count_no'], f"قيد تسوية جرد {count['count_no']}")
        )
        je_id = cur.lastrowid

        line_no = 1
        td = 0
        tc = 0
        for line in adj_lines:
            v = line['total_cost']
            if v == 0: continue
            inv_acc = '1231'
            if line['item_type'] == 'MERCHANDISE': inv_acc = '1234'
            elif line['item_type'] == 'FINISHED_GOODS': inv_acc = '1233'
            elif line['item_type'] == 'SUPPLIES': inv_acc = '1235'

            if v > 0:
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, ?, 'زيادة جرد', ?, 0)""", (je_id, line_no, inv_acc, v))
                td += v; line_no += 1
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, '4231', 'إيرادات - زيادة جرد', 0, ?)""", (je_id, line_no, v))
                tc += v; line_no += 1
            else:
                av = abs(v)
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, '5563', 'عجز جرد', ?, 0)""", (je_id, line_no, av))
                td += av; line_no += 1
                conn.execute("""INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                    VALUES (?, ?, ?, 'نقص مخزون', 0, ?)""", (je_id, line_no, inv_acc, av))
                tc += av; line_no += 1

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?", (td, tc, je_id))
        conn.execute("""UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?""", (je_id, txn_id))
        conn.execute("""UPDATE inventory_counts SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?""", (je_id, cid))

    return jsonify({'success': True, 'message': 'تم ترحيل الجرد',
                    'data': {'count_id': cid, 'transaction_id': txn_id, 'transaction_no': txn_no, 'journal_entry_id': je_id}})


@count_bp.route('/<int:cid>', methods=['DELETE'])
def delete_count(cid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM inventory_counts WHERE id=?", (cid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف جرد مرحّل'}), 400
        conn.execute("DELETE FROM inventory_count_lines WHERE count_id=?", (cid,))
        conn.execute("DELETE FROM inventory_counts WHERE id=?", (cid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
