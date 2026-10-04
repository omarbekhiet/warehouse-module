from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

pr_bp = Blueprint('purchase_returns', __name__)


def _next_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM purchase_returns")
    return f"PRET-{datetime.now().year}-{cur.fetchone()['n']:06d}"


def _next_txn_no(conn, prefix, txn_type):
    cur = conn.execute(
        "SELECT COUNT(*) as n FROM stock_transactions WHERE transaction_type=? AND strftime('%Y', created_at)=strftime('%Y','now')",
        (txn_type,)
    )
    return f"{prefix}-{datetime.now().year}-{cur.fetchone()['n']+1:06d}"


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


@pr_bp.route('/', methods=['GET'])
def list_returns():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('status=?'); vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT pr.*, s.name_ar as supplier_name, w.name_ar as warehouse_name
            FROM purchase_returns pr
            LEFT JOIN suppliers s ON pr.supplier_id = s.id
            LEFT JOIN warehouses w ON pr.warehouse_id = w.id
            WHERE {where}
            ORDER BY pr.id DESC LIMIT 200""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@pr_bp.route('/<int:rid>', methods=['GET'])
def get_return(rid):
    r = db.query(
        """SELECT pr.*, s.name_ar as supplier_name, w.name_ar as warehouse_name
           FROM purchase_returns pr
           LEFT JOIN suppliers s ON pr.supplier_id = s.id
           LEFT JOIN warehouses w ON pr.warehouse_id = w.id
           WHERE pr.id=?""",
        (rid,), one=True
    )
    if not r:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT prl.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name
           FROM purchase_return_lines prl
           JOIN items i ON prl.item_id = i.id
           LEFT JOIN units_of_measure u ON prl.uom_id = u.id
           WHERE prl.return_id=? ORDER BY prl.line_no""",
        (rid,)
    )
    r['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(r)})


@pr_bp.route('/', methods=['POST'])
def create_return():
    d = request.get_json() or {}
    if not d.get('supplier_id') or not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_no(conn)
        cur = conn.execute(
            """INSERT INTO purchase_returns
               (return_no, return_date, original_invoice_id, supplier_id, warehouse_id,
                tax_rate, status, reason, notes)
               VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)""",
            (no, d.get('return_date', datetime.now().strftime('%Y-%m-%d')),
             d.get('original_invoice_id'), d['supplier_id'], d['warehouse_id'],
             d.get('tax_rate', 14), d.get('reason'), d.get('notes'))
        )
        rid = cur.lastrowid

        subtotal = 0
        tax_total = 0

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            qty = float(line['quantity'])
            price = float(line['unit_price'])
            tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
            line_sub = qty * price
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax

            conn.execute(
                """INSERT INTO purchase_return_lines
                   (return_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, tax_rate, line_subtotal, line_tax, line_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, i, line['item_id'], line['uom_id'], qty, base_qty,
                 price, tax_rate, line_sub, line_tax, line_total)
            )
            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE purchase_returns SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), rid)
        )

    return jsonify({'success': True, 'data': {'id': rid, 'return_no': no}}), 201


@pr_bp.route('/<int:rid>/post', methods=['POST'])
def post_return(rid):
    """ترحيل مرتجع الشراء - يخصم من المخزون ويسجل قيد عكسي."""
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM purchase_returns WHERE id=? AND status='DRAFT'", (rid,))
        r = cur.fetchone()
        if not r:
            return jsonify({'success': False, 'message': 'غير موجود أو مرحّل'}), 404
        r = dict(r)

        cur = conn.execute(
            """SELECT prl.*, i.item_type, i.inventory_account FROM purchase_return_lines prl
               JOIN items i ON prl.item_id = i.id
               WHERE prl.return_id=?""",
            (rid,)
        )
        lines = [dict(x) for x in cur.fetchall()]

        # Check stock
        for line in lines:
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (r['warehouse_id'], line['item_id'])
            )
            if float(cur.fetchone()['q']) < float(line['base_quantity']):
                return jsonify({'success': False, 'message': f'الكمية غير كافية للصنف #{line["item_id"]}'}), 400

        # Create ISSUE transaction
        txn_no = _next_txn_no(conn, 'PRT', 'ISSUE')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by)
               VALUES (?, 'ISSUE', ?, ?, 'PURCHASE_RETURN', ?, 'POSTED', ?, 1)""",
            (txn_no, r['return_date'], r['warehouse_id'], r['return_no'],
             f"مرتجع شراء {r['return_no']}")
        )
        txn_id = cur.lastrowid

        # Process lines + deduct stock
        for i, line in enumerate(lines, start=1):
            base_qty = float(line['base_quantity'])
            avg_cost = float(line.get('unit_price', 0))
            line_cost = base_qty * avg_cost

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 line['quantity'], base_qty, avg_cost, line_cost)
            )

            # Deduct from stock
            conn.execute(
                """UPDATE stock_balances
                   SET quantity = quantity - ?,
                       total_value = total_value - ?
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (base_qty, line_cost, r['warehouse_id'], line['item_id'])
            )

        # Journal entry (reversed)
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
               VALUES (?, ?, 'PURCHASE_RETURN', ?, ?, ?, 'POSTED')""",
            (je_no, r['return_date'], rid, r['return_no'], f"قيد مرتجع شراء {r['return_no']}")
        )
        je_id = cur.lastrowid

        line_no = 1
        td = 0
        tc = 0

        # Credit inventory (reverse of purchase)
        inv_by_account = {}
        for line in lines:
            inv_by_account[line['inventory_account']] = inv_by_account.get(line['inventory_account'], 0) + float(line['line_subtotal'])

        for acc, amount in inv_by_account.items():
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, ?, 'مرتجع شراء - مخزون', 0, ?)""",
                (je_id, line_no, acc, round(amount, 2))
            )
            tc += amount; line_no += 1

        # Debit VAT Input (reverse)
        if float(r['tax_amount']) > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, '1251', 'ضريبة مدخلات - مرتجع', 0, ?)""",
                (je_id, line_no, round(float(r['tax_amount']), 2))
            )
            tc += float(r['tax_amount']); line_no += 1

        # Debit clearing
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '1236-01', 'وسيط - مرتجع شراء', ?, 0)""",
            (je_id, line_no, round(float(r['total_amount']), 2))
        )
        td = float(r['total_amount'])

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (round(td, 2), round(tc, 2), je_id))

        conn.execute(
            "UPDATE purchase_returns SET status='POSTED', stock_txn_id=?, journal_entry_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
            (txn_id, je_id, rid)
        )

    return jsonify({'success': True, 'message': 'تم ترحيل مرتجع الشراء', 'data': {'id': rid, 'journal_entry_id': je_id}})


@pr_bp.route('/<int:rid>', methods=['DELETE'])
def delete_return(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_returns WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row or row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف مرتجع مرحّل'}), 400
        conn.execute("DELETE FROM purchase_return_lines WHERE return_id=?", (rid,))
        conn.execute("DELETE FROM purchase_returns WHERE id=?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
