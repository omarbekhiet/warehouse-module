from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal

transfer_bp = Blueprint('transfers', __name__)


def _next_txn_no(conn):
    from datetime import datetime
    cur = conn.execute(
        "SELECT COUNT(*)+1 as n FROM stock_transactions WHERE transaction_type='TRANSFER'"
    )
    n = cur.fetchone()['n']
    return f"TRF-{datetime.now().year}-{n:06d}"


@transfer_bp.route('/', methods=['GET'])
def list_transfers():
    rows = db.query(
        """SELECT t.*, wf.name_ar as from_wh, wt.name_ar as to_wh
           FROM stock_transactions t
           LEFT JOIN warehouses wf ON t.from_warehouse_id = wf.id
           LEFT JOIN warehouses wt ON t.to_warehouse_id = wt.id
           WHERE t.transaction_type='TRANSFER'
           ORDER BY t.id DESC LIMIT 100"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@transfer_bp.route('/', methods=['POST'])
def create_transfer():
    d = request.get_json() or {}
    if not d.get('from_warehouse_id') or not d.get('to_warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    if d['from_warehouse_id'] == d['to_warehouse_id']:
        return jsonify({'success': False, 'message': 'لا يمكن التحويل لنفس المستودع'}), 400

    with db.transaction() as conn:
        txn_no = _next_txn_no(conn)

        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, to_warehouse_id, status, notes, created_by)
               VALUES (?, 'TRANSFER', ?, ?, ?, 'DRAFT', ?, 1)""",
            (txn_no, d.get('transaction_date', '2026-01-01'),
             d['from_warehouse_id'], d['to_warehouse_id'], d.get('notes'))
        )
        txn_id = cur.lastrowid

        for i, line in enumerate(d['lines'], start=1):
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, i, line['item_id'], line.get('uom_id', 1),
                 line['quantity'], 0, 0, line.get('batch_no') or '')
            )

        conn.execute(
            """UPDATE stock_transactions SET
                 total_qty = (SELECT COALESCE(SUM(quantity),0) FROM stock_transaction_lines WHERE transaction_id=?),
                 total_value = (SELECT COALESCE(SUM(total_cost),0) FROM stock_transaction_lines WHERE transaction_id=?)
               WHERE id=?""",
            (txn_id, txn_id, txn_id)
        )

    return jsonify({'success': True, 'data': {'id': txn_id, 'transaction_no': txn_no}}), 201


@transfer_bp.route('/<int:tid>/post', methods=['POST'])
def post_transfer(tid):
    with db.transaction() as conn:
        cur = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND status='DRAFT'",
            (tid,)
        )
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'غير موجود أو مرحّل'}), 404
        txn = dict(txn)

        cur = conn.execute(
            """SELECT l.*, i.name_ar
               FROM stock_transaction_lines l
               JOIN items i ON l.item_id = i.id
               WHERE l.transaction_id=?""",
            (tid,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        for line in lines:
            # Get total balance across all batches (ignore batch_no)
            cur = conn.execute(
                """SELECT COALESCE(SUM(quantity),0) as qty,
                          COALESCE(SUM(total_value),0) as val
                   FROM stock_balances
                   WHERE warehouse_id=? AND item_id=?""",
                (txn['from_warehouse_id'], line['item_id'])
            )
            bal = cur.fetchone()
            available = float(bal['qty']) if bal else 0
            total_val = float(bal['val']) if bal else 0

            if available < float(line['quantity']):
                return jsonify({
                    'success': False,
                    'message': f"رصيد غير كافٍ للصنف {line['name_ar']}. المتاح: {available}"
                }), 400

            unit_cost = (total_val / available) if available > 0 else 0
            total_cost = round_decimal(to_decimal(line['quantity']) * to_decimal(unit_cost))

            # Deduct from source batches
            remaining = float(line['quantity'])
            cur = conn.execute(
                """SELECT id, batch_no, quantity, average_cost FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND quantity > 0
                   ORDER BY batch_no""",
                (txn['from_warehouse_id'], line['item_id'])
            )
            batches = list(cur.fetchall())

            for b in batches:
                if remaining <= 0:
                    break
                take = min(float(b['quantity']), remaining)
                avg = float(b['average_cost']) or 0
                value_deduct = take * avg
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity = quantity - ?,
                           total_value = total_value - ?
                       WHERE id=?""",
                    (take, value_deduct, b['id'])
                )
                remaining -= take

            # Add to target (empty batch)
            cur = conn.execute(
                """SELECT id FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['to_warehouse_id'], line['item_id'])
            )
            existing = cur.fetchone()

            if existing:
                cur = conn.execute(
                    "SELECT quantity, total_value FROM stock_balances WHERE id=?",
                    (existing['id'],)
                )
                cur_row = cur.fetchone()
                new_qty = float(cur_row['quantity']) + float(line['quantity'])
                new_val = float(cur_row['total_value']) + float(total_cost)
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    """UPDATE stock_balances
                       SET quantity=?, total_value=?, average_cost=?
                       WHERE id=?""",
                    (new_qty, new_val, new_avg, existing['id'])
                )
            else:
                conn.execute(
                    """INSERT INTO stock_balances
                       (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                       VALUES (?, ?, '', ?, ?, ?)""",
                    (txn['to_warehouse_id'], line['item_id'],
                     line['quantity'], unit_cost, float(total_cost))
                )

            # Update line costs
            conn.execute(
                "UPDATE stock_transaction_lines SET unit_cost=?, total_cost=? WHERE id=?",
                (unit_cost, float(total_cost), line['id'])
            )

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP WHERE id=?",
            (tid,)
        )

    return jsonify({'success': True, 'message': 'تم الترحيل'})
