from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service

transfer_bp = Blueprint('transfers', __name__)


def _next_txn_no(conn, prefix, txn_type):
    from datetime import datetime
    cur = conn.execute(
        """SELECT COUNT(*) as n FROM stock_transactions
           WHERE transaction_type=? AND strftime('%Y', created_at)=strftime('%Y','now')""",
        (txn_type,)
    )
    n = cur.fetchone()['n'] + 1
    return f"{prefix}-{datetime.now().year}-{n:06d}"


def _get_base_quantity(conn, item_id, uom_id, quantity):
    item = conn.execute(
        "SELECT base_uom_id, medium_uom_id, medium_to_minor_factor, major_uom_id, major_to_medium_factor FROM items WHERE id=?",
        (item_id,)
    ).fetchone()
    if not item:
        return None, None
    if int(uom_id) == int(item['base_uom_id']):
        factor = 1.0
    elif item['medium_uom_id'] and int(uom_id) == int(item['medium_uom_id']):
        factor = float(item['medium_to_minor_factor'] or 1)
    elif item['major_uom_id'] and int(uom_id) == int(item['major_uom_id']):
        factor = float(item['major_to_medium_factor'] or 1) * float(item['medium_to_minor_factor'] or 1)
    else:
        return None, None
    return factor, float(quantity) * factor


@transfer_bp.route('/', methods=['GET'])
def list_transfers():
    rows = db.query(
        """SELECT t.*, 
                  wf.name_ar as from_warehouse_name,
                  wt.name_ar as to_warehouse_name
           FROM stock_transactions t
           LEFT JOIN warehouses wf ON t.from_warehouse_id = wf.id
           LEFT JOIN warehouses wt ON t.to_warehouse_id = wt.id
           WHERE t.transaction_type='TRANSFER'
           ORDER BY t.id DESC LIMIT 100"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@transfer_bp.route('/<int:tid>', methods=['GET'])
def get_transfer(tid):
    txn = db.query("SELECT * FROM stock_transactions WHERE id=?", (tid,), one=True)
    if not txn:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, i.name_ar as item_name, i.code as item_code
           FROM stock_transaction_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.transaction_id=? ORDER BY l.line_no""",
        (tid,)
    )
    txn['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(txn)})


@transfer_bp.route('/', methods=['POST'])
def create_transfer():
    d = request.get_json() or {}
    if not d.get('from_warehouse_id') or not d.get('to_warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    movement_code = d.get('movement_code', 'TRANS')

    with db.transaction() as conn:
        txn_no = _next_txn_no(conn, 'TRF', 'TRANSFER')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, to_warehouse_id, reference_type, reference_no,
                status, notes, created_by, movement_code)
               VALUES (?, 'TRANSFER', ?, ?, ?, ?, ?, 'DRAFT', ?, 1, ?)""",
            (txn_no, d.get('transaction_date', '2026-01-01'),
             d['from_warehouse_id'], d['to_warehouse_id'],
             d.get('reference_type'), d.get('reference_no'),
             d.get('notes'), movement_code)
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_val = 0
        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(
                conn, line['item_id'], line['uom_id'], line['quantity']
            )
            if base_qty is None:
                return jsonify({'success': False, 'message': f'الوحدة غير مرتبطة بالصنف #{line["item_id"]}'}), 400

            cur2 = conn.execute(
                """SELECT average_cost FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (d['from_warehouse_id'], line['item_id'])
            )
            bal = cur2.fetchone()
            if not bal:
                return jsonify({'success': False, 'message': f'لا يوجد رصيد للصنف #{line["item_id"]}'}), 400

            unit_cost = float(bal['average_cost'])
            total_cost = round_decimal(to_decimal(base_qty) * to_decimal(unit_cost))

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity,
                    base_quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 float(line['quantity']), float(base_qty), unit_cost,
                 float(total_cost), line.get('batch_no') or '')
            )
            total_qty += base_qty
            total_val += float(total_cost)

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_val, 4), txn_id)
        )

    return jsonify({'success': True, 'data': {'id': txn_id, 'transaction_no': txn_no}}), 201


@transfer_bp.route('/<int:tid>/post', methods=['POST'])
def post_transfer(tid):
    with db.transaction() as conn:
        cur = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND status='DRAFT'", (tid,)
        )
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الحركة غير موجودة أو مرحّلة'}), 404
        txn = dict(txn)

        cur = conn.execute(
            """SELECT l.*, i.item_type FROM stock_transaction_lines l
               LEFT JOIN items i ON l.item_id = i.id
               WHERE l.transaction_id=?""",
            (tid,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        # اخصم من المستودع المصدر
        for line in lines:
            cur = conn.execute(
                """SELECT id, quantity, total_value FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['from_warehouse_id'], line['item_id'])
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) - float(line['base_quantity'] or line['quantity'])
                new_val = float(existing['total_value']) - float(line['total_cost'])
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    "UPDATE stock_balances SET quantity=?, total_value=?, average_cost=? WHERE id=?",
                    (new_qty, new_val, new_avg, existing['id'])
                )

        # أضف للمستودع المستلم
        for line in lines:
            cur = conn.execute(
                """SELECT id, quantity, total_value FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['to_warehouse_id'], line['item_id'])
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) + float(line['base_quantity'] or line['quantity'])
                new_val = float(existing['total_value']) + float(line['total_cost'])
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    "UPDATE stock_balances SET quantity=?, total_value=?, average_cost=? WHERE id=?",
                    (new_qty, new_val, new_avg, existing['id'])
                )
            else:
                qty = float(line['base_quantity'] or line['quantity'])
                avg = float(line['unit_cost'])
                conn.execute(
                    """INSERT INTO stock_balances
                       (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                       VALUES (?, ?, '', ?, ?, ?)""",
                    (txn['to_warehouse_id'], line['item_id'], qty, avg, float(line['total_cost']))
                )

        # توليد القيد المحاسبي
        je_id = accounting_service.create_journal_entry(conn, txn, lines)

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, tid)
        )

    return jsonify({'success': True, 'message': 'تم الترحيل', 'data': {'journal_entry_id': je_id}})