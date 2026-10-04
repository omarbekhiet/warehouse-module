from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

po_bp = Blueprint('purchase_orders', __name__)


def _next_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM purchase_orders")
    return f"PO-{datetime.now().year}-{cur.fetchone()['n']:06d}"


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


@po_bp.route('/', methods=['GET'])
def list_pos():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('po.status = ?')
        vals.append(request.args.get('status'))
    if request.args.get('supplier_id'):
        cond.append('po.supplier_id = ?')
        vals.append(request.args.get('supplier_id'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT po.*, s.name_ar as supplier_name, w.name_ar as warehouse_name
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            LEFT JOIN warehouses w ON po.warehouse_id = w.id
            WHERE {where}
            ORDER BY po.id DESC LIMIT 200""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@po_bp.route('/<int:po_id>', methods=['GET'])
def get_po(po_id):
    po = db.query(
        """SELECT po.*, s.name_ar as supplier_name, s.code as supplier_code,
                  w.name_ar as warehouse_name
           FROM purchase_orders po
           LEFT JOIN suppliers s ON po.supplier_id = s.id
           LEFT JOIN warehouses w ON po.warehouse_id = w.id
           WHERE po.id=?""",
        (po_id,), one=True
    )
    if not po:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT pol.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name
           FROM purchase_order_lines pol
           JOIN items i ON pol.item_id = i.id
           LEFT JOIN units_of_measure u ON pol.uom_id = u.id
           WHERE pol.po_id=? ORDER BY pol.line_no""",
        (po_id,)
    )
    po['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(po)})


@po_bp.route('/', methods=['POST'])
def create_po():
    d = request.get_json() or {}
    if not d.get('supplier_id') or not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_no(conn)
        cur = conn.execute(
            """INSERT INTO purchase_orders
               (po_no, po_date, supplier_id, warehouse_id, expected_date,
                tax_rate, status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, 1)""",
            (no, d.get('po_date', datetime.now().strftime('%Y-%m-%d')),
             d['supplier_id'], d['warehouse_id'], d.get('expected_date'),
             d.get('tax_rate', 14), d.get('notes'))
        )
        po_id = cur.lastrowid

        subtotal = 0
        tax_total = 0

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            qty = float(line['quantity'])
            price = float(line['unit_price'])
            disc_pct = float(line.get('discount_pct', 0))
            tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
            line_sub = qty * price * (1 - disc_pct/100)
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax

            conn.execute(
                """INSERT INTO purchase_order_lines
                   (po_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, discount_pct, tax_rate, line_subtotal, line_tax, line_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (po_id, i, line['item_id'], line['uom_id'], qty, base_qty,
                 price, disc_pct, tax_rate, line_sub, line_tax, line_total)
            )
            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE purchase_orders SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), po_id)
        )

    return jsonify({'success': True, 'data': {'id': po_id, 'po_no': no}}), 201


@po_bp.route('/<int:po_id>', methods=['PUT'])
def update_po(po_id):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_orders WHERE id=?", (po_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل أمر شراء معتمد أو مستلم'}), 400

        conn.execute(
            """UPDATE purchase_orders
               SET po_date=?, supplier_id=?, warehouse_id=?, expected_date=?,
                   tax_rate=?, notes=?
               WHERE id=?""",
            (d.get('po_date'), d['supplier_id'], d['warehouse_id'],
             d.get('expected_date'), d.get('tax_rate', 14), d.get('notes'), po_id)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM purchase_order_lines WHERE po_id=?", (po_id,))
            subtotal = 0
            tax_total = 0
            for i, line in enumerate(d['lines'], start=1):
                factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
                if base_qty is None:
                    return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400
                qty = float(line['quantity'])
                price = float(line['unit_price'])
                disc_pct = float(line.get('discount_pct', 0))
                tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
                line_sub = qty * price * (1 - disc_pct/100)
                line_tax = line_sub * tax_rate / 100
                line_total = line_sub + line_tax
                conn.execute(
                    """INSERT INTO purchase_order_lines
                       (po_id, line_no, item_id, uom_id, quantity, base_quantity,
                        unit_price, discount_pct, tax_rate, line_subtotal, line_tax, line_total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (po_id, i, line['item_id'], line['uom_id'], qty, base_qty,
                     price, disc_pct, tax_rate, line_sub, line_tax, line_total)
                )
                subtotal += line_sub
                tax_total += line_tax
            conn.execute(
                "UPDATE purchase_orders SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
                (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), po_id)
            )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@po_bp.route('/<int:po_id>/approve', methods=['POST'])
def approve_po(po_id):
    """اعتماد أمر الشراء."""
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_orders WHERE id=?", (po_id,))
        row = cur.fetchone()
        if not row or row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن اعتماد المسودة فقط'}), 400
        conn.execute(
            "UPDATE purchase_orders SET status='APPROVED', approved_at=CURRENT_TIMESTAMP, approved_by=1 WHERE id=?",
            (po_id,)
        )
    return jsonify({'success': True, 'message': 'تم الاعتماد'})


@po_bp.route('/<int:po_id>/reject', methods=['POST'])
def reject_po(po_id):
    with db.transaction() as conn:
        conn.execute("UPDATE purchase_orders SET status='REJECTED' WHERE id=? AND status='DRAFT'", (po_id,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@po_bp.route('/<int:po_id>/restore', methods=['POST'])
def restore_po(po_id):
    with db.transaction() as conn:
        conn.execute("UPDATE purchase_orders SET status='DRAFT' WHERE id=? AND status='REJECTED'", (po_id,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@po_bp.route('/<int:po_id>/receive', methods=['POST'])
def receive_po(po_id):
    """استلام أمر الشراء → إنشاء إذن استلام (بدون فاتورة)."""
    d = request.get_json() or {}
    received_lines = d.get('lines', [])  # [{line_id, received_qty}]
    
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM purchase_orders WHERE id=? AND status='APPROVED'", (po_id,))
        po = cur.fetchone()
        if not po:
            return jsonify({'success': False, 'message': 'أمر الشراء غير موجود أو غير معتمد'}), 404
        po = dict(po)

        cur = conn.execute(
            """SELECT pol.*, i.item_type, i.inventory_account
               FROM purchase_order_lines pol
               JOIN items i ON pol.item_id = i.id
               WHERE pol.po_id=?""",
            (po_id,)
        )
        all_lines = [dict(r) for r in cur.fetchall()]
        
        # Filter received lines
        lines = []
        for ol in all_lines:
            if received_lines:
                recv = next((l for l in received_lines if l['line_id'] == ol['id']), None)
                if not recv or float(recv.get('received_qty', 0)) <= 0:
                    continue
                qty_to_receive = float(recv['received_qty'])
            else:
                qty_to_receive = float(ol['quantity']) - float(ol['received_qty'] or 0)
            
            if qty_to_receive <= 0:
                continue
            
            lines.append({**ol, 'receive_qty': qty_to_receive})
        
        if not lines:
            return jsonify({'success': False, 'message': 'لا توجد بنود للاستلام'}), 400

        # Create RECEIPT
        txn_no = _next_txn_no(conn, 'GRN', 'RECEIPT')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, reference_type, reference_no,
                status, notes, created_by, invoice_type)
               VALUES (?, 'RECEIPT', ?, ?, 'PURCHASE_ORDER', ?, 'DRAFT', ?, 1, 'PO')""",
            (txn_no, d.get('receive_date', datetime.now().strftime('%Y-%m-%d')),
             po['warehouse_id'], po['po_no'], f"استلام من أمر شراء {po['po_no']}")
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_val = 0

        for i, line in enumerate(lines, start=1):
            qty = float(line['receive_qty'])
            factor = float(line['base_quantity']) / float(line['quantity']) if float(line['quantity']) > 0 else 1
            base_qty = qty * factor
            unit_cost_base = float(line['unit_price']) / factor if factor > 0 else float(line['unit_price'])
            total_cost = base_qty * unit_cost_base

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 qty, base_qty, unit_cost_base, total_cost)
            )

            # Update PO line received_qty
            conn.execute(
                "UPDATE purchase_order_lines SET received_qty = received_qty + ? WHERE id=?",
                (qty, line['id'])
            )

            total_qty += base_qty
            total_val += total_cost

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_val, 4), txn_id)
        )

        # Update stock balances
        for line in lines:
            qty = float(line['receive_qty'])
            factor = float(line['base_quantity']) / float(line['quantity']) if float(line['quantity']) > 0 else 1
            base_qty = qty * factor
            unit_cost_base = float(line['unit_price']) / factor if factor > 0 else float(line['unit_price'])
            total_cost = base_qty * unit_cost_base

            cur = conn.execute(
                "SELECT id, quantity, total_value FROM stock_balances WHERE warehouse_id=? AND item_id=? AND batch_no=''",
                (po['warehouse_id'], line['item_id'])
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) + base_qty
                new_val = float(existing['total_value']) + total_cost
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute("UPDATE stock_balances SET quantity=?, total_value=?, average_cost=? WHERE id=?",
                             (new_qty, new_val, new_avg, existing['id']))
            else:
                conn.execute(
                    """INSERT INTO stock_balances (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                       VALUES (?, ?, '', ?, ?, ?)""",
                    (po['warehouse_id'], line['item_id'], base_qty, unit_cost_base, total_cost)
                )

        # Journal: Debit inventory, Credit clearing (1236-01)
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
               VALUES (?, ?, 'PURCHASE_ORDER', ?, ?, ?, 'POSTED')""",
            (je_no, d.get('receive_date', datetime.now().strftime('%Y-%m-%d')),
             po_id, po['po_no'], f"استلام أمر شراء {po['po_no']}")
        )
        je_id = cur.lastrowid

        inv_by_account = {}
        for line in lines:
            inv_by_account[line['inventory_account']] = inv_by_account.get(line['inventory_account'], 0) + (float(line['receive_qty']) * float(line['unit_price']))

        line_no = 1
        td = 0
        tc = 0

        for acc, amount in inv_by_account.items():
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, ?, 'استلام من PO - مخزون', ?, 0)""",
                (je_id, line_no, acc, round(amount, 2))
            )
            td += amount
            line_no += 1

        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '1236-01', 'وسيط - استلام PO', 0, ?)""",
            (je_id, line_no, round(td, 2))
        )
        tc = td

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (round(td, 2), round(tc, 2), je_id))

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, txn_id)
        )

        # Check if fully received → mark COMPLETED
        cur = conn.execute("SELECT SUM(quantity) as total, SUM(received_qty) as recv FROM purchase_order_lines WHERE po_id=?", (po_id,))
        r = cur.fetchone()
        if float(r['recv'] or 0) >= float(r['total'] or 0):
            conn.execute("UPDATE purchase_orders SET status='COMPLETED', stock_txn_id=? WHERE id=?", (txn_id, po_id))
        else:
            conn.execute("UPDATE purchase_orders SET status='PARTIAL', stock_txn_id=? WHERE id=?", (txn_id, po_id))

    return jsonify({
        'success': True,
        'message': f'تم الاستلام - إذن {txn_no}',
        'data': {'po_id': po_id, 'stock_txn_id': txn_id, 'stock_txn_no': txn_no, 'journal_entry_id': je_id}
    })


@po_bp.route('/<int:po_id>', methods=['DELETE'])
def delete_po(po_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_orders WHERE id=?", (po_id,))
        row = cur.fetchone()
        if not row or row['status'] in ('COMPLETED', 'PARTIAL'):
            return jsonify({'success': False, 'message': 'لا يمكن حذف أمر شراء مستلم'}), 400
        conn.execute("DELETE FROM purchase_order_lines WHERE po_id=?", (po_id,))
        conn.execute("DELETE FROM purchase_orders WHERE id=?", (po_id,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
