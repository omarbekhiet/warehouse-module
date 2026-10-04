from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

sales_bp = Blueprint('sales_invoices', __name__)


def _next_invoice_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM sales_invoices")
    return f"SINV-{datetime.now().year}-{cur.fetchone()['n']:06d}"


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


@sales_bp.route('/', methods=['GET'])
def list_sales():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('si.status = ?')
        vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT si.*, c.name_ar as customer_name, w.name_ar as warehouse_name
            FROM sales_invoices si
            LEFT JOIN customers c ON si.customer_id = c.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE {where}
            ORDER BY si.id DESC LIMIT 200""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@sales_bp.route('/<int:inv_id>', methods=['GET'])
def get_sale(inv_id):
    inv = db.query(
        """SELECT si.*, c.name_ar as customer_name, c.code as customer_code,
                  w.name_ar as warehouse_name
           FROM sales_invoices si
           LEFT JOIN customers c ON si.customer_id = c.id
           LEFT JOIN warehouses w ON si.warehouse_id = w.id
           WHERE si.id=?""",
        (inv_id,), one=True
    )
    if not inv:
        return jsonify({'success': False, 'message': 'غير موجودة'}), 404
    lines = db.query(
        """SELECT sil.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name, u.code as uom_code
           FROM sales_invoice_lines sil
           JOIN items i ON sil.item_id = i.id
           LEFT JOIN units_of_measure u ON sil.uom_id = u.id
           WHERE sil.invoice_id=? ORDER BY sil.line_no""",
        (inv_id,)
    )
    inv['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(inv)})


@sales_bp.route('/', methods=['POST'])
def create_sale():
    d = request.get_json() or {}
    if not d.get('customer_id') or not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        inv_no = _next_invoice_no(conn)
        cur = conn.execute(
            """INSERT INTO sales_invoices
               (invoice_no, invoice_date, customer_id, warehouse_id,
                tax_rate, status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, 1)""",
            (inv_no, d.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
             d['customer_id'], d['warehouse_id'],
             d.get('tax_rate', 14), d.get('notes'))
        )
        inv_id = cur.lastrowid

        subtotal = 0
        tax_total = 0
        cogs_total = 0

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            # Get avg cost
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q, COALESCE(SUM(total_value),0) as v FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (d['warehouse_id'], line['item_id'])
            )
            bal = cur.fetchone()
            available = float(bal['q']) if bal else 0
            total_val = float(bal['v']) if bal else 0
            avg_cost = (total_val / available) if available > 0 else 0
            line_cost = float(base_qty) * avg_cost
            cogs_total += line_cost

            qty = float(line['quantity'])
            price = float(line['unit_price'])
            disc_pct = float(line.get('discount_pct', 0))
            tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
            line_sub = qty * price * (1 - disc_pct/100)
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax

            conn.execute(
                """INSERT INTO sales_invoice_lines
                   (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, unit_cost, discount_pct, tax_rate,
                    line_subtotal, line_tax, line_total, line_cost)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (inv_id, i, line['item_id'], line['uom_id'],
                 qty, base_qty, price, avg_cost, disc_pct, tax_rate,
                 line_sub, line_tax, line_total, line_cost)
            )
            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE sales_invoices SET subtotal=?, tax_amount=?, total_amount=?, cogs_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), round(cogs_total, 2), inv_id)
        )

    return jsonify({'success': True, 'data': {'id': inv_id, 'invoice_no': inv_no}}), 201


@sales_bp.route('/<int:inv_id>', methods=['PUT'])
def update_sale(inv_id):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل فاتورة مرحّلة'}), 400

        conn.execute(
            """UPDATE sales_invoices
               SET invoice_date=?, customer_id=?, warehouse_id=?, tax_rate=?, notes=?
               WHERE id=?""",
            (d.get('invoice_date'), d['customer_id'], d['warehouse_id'],
             d.get('tax_rate', 14), d.get('notes'), inv_id)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM sales_invoice_lines WHERE invoice_id=?", (inv_id,))
            subtotal = 0
            tax_total = 0
            cogs_total = 0
            for i, line in enumerate(d['lines'], start=1):
                factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
                if base_qty is None:
                    return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400
                cur = conn.execute(
                    "SELECT COALESCE(SUM(quantity),0) as q, COALESCE(SUM(total_value),0) as v FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                    (d['warehouse_id'], line['item_id'])
                )
                bal = cur.fetchone()
                available = float(bal['q']) if bal else 0
                total_val = float(bal['v']) if bal else 0
                avg_cost = (total_val / available) if available > 0 else 0
                line_cost = float(base_qty) * avg_cost
                cogs_total += line_cost

                qty = float(line['quantity'])
                price = float(line['unit_price'])
                disc_pct = float(line.get('discount_pct', 0))
                tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
                line_sub = qty * price * (1 - disc_pct/100)
                line_tax = line_sub * tax_rate / 100
                line_total = line_sub + line_tax

                conn.execute(
                    """INSERT INTO sales_invoice_lines
                       (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                        unit_price, unit_cost, discount_pct, tax_rate,
                        line_subtotal, line_tax, line_total, line_cost)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (inv_id, i, line['item_id'], line['uom_id'],
                     qty, base_qty, price, avg_cost, disc_pct, tax_rate,
                     line_sub, line_tax, line_total, line_cost)
                )
                subtotal += line_sub
                tax_total += line_tax

            conn.execute(
                "UPDATE sales_invoices SET subtotal=?, tax_amount=?, total_amount=?, cogs_amount=? WHERE id=?",
                (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), round(cogs_total, 2), inv_id)
            )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@sales_bp.route('/<int:inv_id>/reject', methods=['POST'])
def reject_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row or row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن رفض المسودة فقط'}), 400
        conn.execute("UPDATE sales_invoices SET status='REJECTED' WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@sales_bp.route('/<int:inv_id>/restore', methods=['POST'])
def restore_sale(inv_id):
    with db.transaction() as conn:
        conn.execute("UPDATE sales_invoices SET status='DRAFT' WHERE id=? AND status='REJECTED'", (inv_id,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@sales_bp.route('/<int:inv_id>', methods=['DELETE'])
def delete_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM sales_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row or row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف فاتورة مرحّلة'}), 400
        conn.execute("DELETE FROM sales_invoice_lines WHERE invoice_id=?", (inv_id,))
        conn.execute("DELETE FROM sales_invoices WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@sales_bp.route('/<int:inv_id>/post', methods=['POST'])
def post_sale(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM sales_invoices WHERE id=? AND status IN ('DRAFT','REJECTED')", (inv_id,))
        inv = cur.fetchone()
        if not inv:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        inv = dict(inv)

        cur = conn.execute(
            """SELECT sil.*, i.item_type FROM sales_invoice_lines sil
               JOIN items i ON sil.item_id = i.id
               WHERE sil.invoice_id=?""",
            (inv_id,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        # Stock check
        for line in lines:
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (inv['warehouse_id'], line['item_id'])
            )
            available = float(cur.fetchone()['q'])
            if available < float(line['base_quantity']):
                return jsonify({'success': False, 'message': f'الكمية غير كافية للصنف. المتاح: {available}'}), 400

        txn_no = _next_txn_no(conn, 'DEL', 'ISSUE')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by, invoice_id, invoice_type)
               VALUES (?, 'ISSUE', ?, ?, 'SALES_INVOICE', ?, 'DRAFT', ?, 1, ?, 'SALES')""",
            (txn_no, inv['invoice_date'], inv['warehouse_id'],
             inv['invoice_no'], f"صرف من فاتورة {inv['invoice_no']}", inv_id)
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_cost = 0
        for i, line in enumerate(lines, start=1):
            base_qty = float(line['base_quantity'])
            unit_cost_base = float(line['unit_cost'])
            line_cost = float(line['line_cost'])
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 line['quantity'], base_qty, unit_cost_base, line_cost)
            )
            conn.execute(
                """UPDATE stock_balances
                   SET quantity = quantity - ?,
                       total_value = total_value - ?,
                       average_cost = CASE WHEN quantity - ? > 0
                         THEN (total_value - ?) / (quantity - ?) ELSE 0 END
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (base_qty, line_cost, base_qty, line_cost, base_qty,
                 inv['warehouse_id'], line['item_id'])
            )
            total_qty += base_qty
            total_cost += line_cost

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_cost, 4), txn_id)
        )

        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
               VALUES (?, ?, 'SALES_INVOICE', ?, ?, ?, 'POSTED')""",
            (je_no, inv['invoice_date'], inv_id, inv['invoice_no'], f"قيد فاتورة بيع {inv['invoice_no']}")
        )
        je_id = cur.lastrowid

        line_no = 1
        td = 0
        tc = 0

        # Debit AR
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '1221', 'ذمم العملاء', ?, 0)""",
            (je_id, line_no, round(float(inv['total_amount']), 2))
        )
        td += float(inv['total_amount']); line_no += 1

        # Credit Revenue
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '4111', 'إيرادات المبيعات', 0, ?)""",
            (je_id, line_no, round(float(inv['subtotal']), 2))
        )
        tc += float(inv['subtotal']); line_no += 1

        # Credit VAT Output
        if float(inv['tax_amount']) > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, '2231', 'ضريبة مخرجات', 0, ?)""",
                (je_id, line_no, round(float(inv['tax_amount']), 2))
            )
            tc += float(inv['tax_amount']); line_no += 1

        # COGS
        inv_by_account = {}
        for line in lines:
            item_info = conn.execute("SELECT inventory_account FROM items WHERE id=?", (line['item_id'],)).fetchone()
            acc = item_info['inventory_account'] if item_info else '1234'
            inv_by_account[acc] = inv_by_account.get(acc, 0) + float(line['line_cost'])

        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '3000', 'تكلفة المبيعات', ?, 0)""",
            (je_id, line_no, round(float(inv['cogs_amount']), 2))
        )
        td += float(inv['cogs_amount']); line_no += 1

        for acc, amount in inv_by_account.items():
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, ?, 'مخزون مصروف', 0, ?)""",
                (je_id, line_no, acc, round(amount, 2))
            )
            tc += amount; line_no += 1

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (round(td, 2), round(tc, 2), je_id))

        conn.execute(
            "UPDATE sales_invoices SET status='POSTED', stock_txn_id=?, journal_entry_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
            (txn_id, je_id, inv_id)
        )
        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, txn_id)
        )

    return jsonify({
        'success': True,
        'message': 'تم ترحيل الفاتورة',
        'data': {'invoice_id': inv_id, 'stock_txn_id': txn_id, 'journal_entry_id': je_id}
    })
