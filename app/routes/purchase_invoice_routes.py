from flask import Blueprint, request, jsonify
from app.database import db
from app.services.settings_service import (
    get_suppliers, get_accounting,
    get_supplier_balance, get_supplier_pending_po_count,
    check_period, resolve_warehouse, get_inventory
)
from app.utils import json_safe, to_decimal, round_decimal, get_user_id, enrich_with_user
from datetime import datetime

invoice_bp = Blueprint('purchase_invoices', __name__)


def _next_invoice_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM purchase_invoices")
    return f"PINV-{datetime.now().year}-{cur.fetchone()['n']:06d}"


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


@invoice_bp.route('/', methods=['GET'])
def list_invoices():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('pi.status = ?')
        vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT pi.*, s.name_ar as supplier_name, w.name_ar as warehouse_name
            FROM purchase_invoices pi
            LEFT JOIN suppliers s ON pi.supplier_id = s.id
            LEFT JOIN warehouses w ON pi.warehouse_id = w.id
            WHERE {where}
            ORDER BY pi.id DESC LIMIT 200""",
        vals
    )
    rows = enrich_with_user(rows)
    return jsonify({'success': True, 'data': json_safe(rows)})
    

@invoice_bp.route('/<int:inv_id>', methods=['GET'])
def get_invoice(inv_id):
    inv = db.query(
        """SELECT pi.*, s.name_ar as supplier_name, s.code as supplier_code,
                  w.name_ar as warehouse_name
           FROM purchase_invoices pi
           LEFT JOIN suppliers s ON pi.supplier_id = s.id
           LEFT JOIN warehouses w ON pi.warehouse_id = w.id
           WHERE pi.id=?""",
        (inv_id,), one=True
    )
    if not inv:
        return jsonify({'success': False, 'message': 'غير موجودة'}), 404
    lines = db.query(
        """SELECT pil.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name, u.code as uom_code
           FROM purchase_invoice_lines pil
           JOIN items i ON pil.item_id = i.id
           LEFT JOIN units_of_measure u ON pil.uom_id = u.id
           WHERE pil.invoice_id=? ORDER BY pil.line_no""",
        (inv_id,)
    )
    inv['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(inv)})


# ==========================================
# دوال التحقق من سياسات الموردين
# ==========================================

def _validate_purchase_policies(supplier_id, warehouse_id, lines):
    """
    التحقق من سياسات الموردين قبل إنشاء/تعديل فاتورة شراء
    """
    sup_settings = get_suppliers()
    acc_settings = get_accounting()

    supplier = db.query(
        "SELECT id, name_ar, payment_terms FROM suppliers WHERE id=?",
        (supplier_id,), one=True
    )
    if not supplier:
        return {'ok': False, 'message': 'المورد غير موجود', 'code': 404}

    if sup_settings.get('require_po_before_invoice'):
        po_count = db.query(
            """SELECT COUNT(*) AS cnt FROM purchase_orders
               WHERE supplier_id=? AND status IN ('APPROVED', 'PARTIAL', 'COMPLETED')""",
            (supplier_id,), one=True
        )
        approved_pos = int(po_count['cnt'] or 0) if po_count else 0

        if approved_pos == 0:
            return {
                'ok': False,
                'message': (
                    f"لا يمكن إنشاء فاتورة شراء بدون أمر شراء معتمد - المورد '{supplier['name_ar']}' "
                    f"ليس لديه أي أمر شراء. الرجاء إنشاء أمر شراء أولاً."
                ),
                'code': 400
            }

    return {'ok': True}


@invoice_bp.route('/', methods=['POST'])
def create_invoice():
    default_discount = float(get_suppliers().get('default_discount', 0))
    d = request.get_json() or {}
    if not d.get('supplier_id') or not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    v = _validate_purchase_policies(d['supplier_id'], d['warehouse_id'], d['lines'])
    if not v['ok']:
        return jsonify({'success': False, 'message': v['message']}), v.get('code', 400)

    _date = d.get('invoice_date', datetime.now().strftime('%Y-%m-%d'))
    _period_check = check_period(_date)
    if not _period_check['ok']:
        return jsonify({'success': False, 'message': _period_check['message']}), _period_check.get('code', 400)

    _wh_input = d.get('warehouse_id') if 'd' in dir() else None
    wh_result = resolve_warehouse(_wh_input)
    if not wh_result['ok']:
        return jsonify({'success': False, 'message': wh_result['message']}), wh_result.get('code', 400)
    d['warehouse_id'] = wh_result['warehouse_id']

    with db.transaction() as conn:
        inv_no = _next_invoice_no(conn)
        user_id = get_user_id()

        cur = conn.execute(
            """INSERT INTO purchase_invoices
               (invoice_no, invoice_date, supplier_id, supplier_invoice_no,
                warehouse_id, tax_rate, status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)""",
            (inv_no, d.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
             d['supplier_id'], d.get('supplier_invoice_no'),
             d['warehouse_id'], d.get('tax_rate', get_accounting().get('default_vat_rate', 14)),
             d.get('notes'), user_id)
        )
        inv_id = cur.lastrowid

        subtotal = 0
        tax_total = 0

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            qty = float(line['quantity'])
            price = float(line['unit_price'])
            disc_pct = float(line.get('discount_pct', default_discount))
            tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
            line_sub = qty * price * (1 - disc_pct/100)
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax

            _batch = (line.get('batch_no') or '').strip()
            _expiry = line.get('expiry_date') or None

            conn.execute(
                """INSERT INTO purchase_invoice_lines
                   (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, discount_pct, tax_rate, line_subtotal, line_tax, line_total,
                    batch_no, expiry_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (inv_id, i, line['item_id'], line['uom_id'], qty, base_qty,
                 price, disc_pct, tax_rate, line_sub, line_tax, line_total,
                 _batch, _expiry)
            )
            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE purchase_invoices SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), inv_id)
        )

    return jsonify({'success': True, 'data': {'id': inv_id, 'invoice_no': inv_no}}), 201


@invoice_bp.route('/<int:inv_id>', methods=['PUT'])
def update_invoice(inv_id):
    default_discount = float(get_suppliers().get('default_discount', 0))
    d = request.get_json() or {}
    if d.get('supplier_id') and d.get('warehouse_id') and d.get('lines'):
        v = _validate_purchase_policies(d['supplier_id'], d['warehouse_id'], d['lines'])
        if not v['ok']:
            return jsonify({'success': False, 'message': v['message']}), v.get('code', 400)

    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل فاتورة مرحّلة'}), 400

        conn.execute(
            """UPDATE purchase_invoices
               SET invoice_date=?, supplier_id=?, supplier_invoice_no=?,
                   warehouse_id=?, tax_rate=?, notes=?
               WHERE id=?""",
            (d.get('invoice_date'), d['supplier_id'], d.get('supplier_invoice_no'),
             d['warehouse_id'], d.get('tax_rate', 14), d.get('notes'), inv_id)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM purchase_invoice_lines WHERE invoice_id=?", (inv_id,))
            subtotal = 0
            tax_total = 0
            for i, line in enumerate(d['lines'], start=1):
                factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
                if base_qty is None:
                    return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400
                qty = float(line['quantity'])
                price = float(line['unit_price'])
                disc_pct = float(line.get('discount_pct', default_discount))
                tax_rate = float(line.get('tax_rate', d.get('tax_rate', 14)))
                line_sub = qty * price * (1 - disc_pct/100)
                line_tax = line_sub * tax_rate / 100
                line_total = line_sub + line_tax
                conn.execute(
                    """INSERT INTO purchase_invoice_lines
                       (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                        unit_price, discount_pct, tax_rate, line_subtotal, line_tax, line_total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (inv_id, i, line['item_id'], line['uom_id'], qty, base_qty,
                     price, disc_pct, tax_rate, line_sub, line_tax, line_total)
                )
                subtotal += line_sub
                tax_total += line_tax
            conn.execute(
                "UPDATE purchase_invoices SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
                (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), inv_id)
            )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@invoice_bp.route('/<int:inv_id>/reject', methods=['POST'])
def reject_invoice(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        if row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن رفض المسودة فقط'}), 400
        conn.execute("UPDATE purchase_invoices SET status='REJECTED' WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@invoice_bp.route('/<int:inv_id>/restore', methods=['POST'])
def restore_invoice(inv_id):
    with db.transaction() as conn:
        conn.execute("UPDATE purchase_invoices SET status='DRAFT' WHERE id=? AND status='REJECTED'", (inv_id,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@invoice_bp.route('/<int:inv_id>', methods=['DELETE'])
def delete_invoice(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_invoices WHERE id=?", (inv_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجودة'}), 404
        if row['status'] == 'POSTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف فاتورة مرحّلة'}), 400
        conn.execute("DELETE FROM purchase_invoice_lines WHERE invoice_id=?", (inv_id,))
        conn.execute("DELETE FROM purchase_invoices WHERE id=?", (inv_id,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


@invoice_bp.route('/<int:inv_id>/post', methods=['POST'])
def post_invoice(inv_id):
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM purchase_invoices WHERE id=? AND status IN ('DRAFT','REJECTED')", (inv_id,))
        inv = cur.fetchone()
        if not inv:
            return jsonify({'success': False, 'message': 'غير موجودة أو مرحّلة'}), 404
        inv = dict(inv)

        cur = conn.execute(
            """SELECT pil.*, i.item_type FROM purchase_invoice_lines pil
               JOIN items i ON pil.item_id = i.id
               WHERE pil.invoice_id=?""",
            (inv_id,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        inv_settings = get_inventory()
        batch_enabled = bool(inv_settings.get('batch_tracking', False))
        expiry_enabled = bool(inv_settings.get('expiry_tracking', False))

        txn_no = _next_txn_no(conn, 'REC', 'RECEIPT')
        user_id = get_user_id()

        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, reference_type, reference_no,
                status, notes, created_by, invoice_id, invoice_type)
               VALUES (?, 'RECEIPT', ?, ?, 'PURCHASE_INVOICE', ?, 'DRAFT', ?, ?, ?, 'PURCHASE')""",
            (txn_no, inv['invoice_date'], inv['warehouse_id'],
             inv['invoice_no'], f"استلام من فاتورة {inv['invoice_no']}", user_id, inv_id)
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_val = 0
        for i, line in enumerate(lines, start=1):
            factor = float(line['base_quantity']) / float(line['quantity']) if float(line['quantity']) > 0 else 1
            unit_cost_base = round_decimal(to_decimal(line['unit_price']) / to_decimal(factor), 6)
            total_cost = round_decimal(to_decimal(line['base_quantity']) * unit_cost_base)

            _batch = (line.get('batch_no') or '').strip() if batch_enabled else ''
            _expiry = (line.get('expiry_date') or None) if expiry_enabled else None

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no, expiry_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 line['quantity'], line['base_quantity'],
                 float(unit_cost_base), float(total_cost),
                 _batch, _expiry)
            )
            total_qty += float(line['base_quantity'])
            total_val += float(total_cost)

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_val, 4), txn_id)
        )

        for line in lines:
            base_qty = float(line['base_quantity'])
            factor = base_qty / float(line['quantity']) if float(line['quantity']) > 0 else 1
            unit_cost_base = float(line['unit_price']) / factor
            total_cost = base_qty * unit_cost_base

            _batch = (line.get('batch_no') or '').strip() if batch_enabled else ''
            _expiry = (line.get('expiry_date') or None) if expiry_enabled else None

            cur = conn.execute(
                "SELECT id, quantity, total_value FROM stock_balances WHERE warehouse_id=? AND item_id=? AND batch_no=?",
                (inv['warehouse_id'], line['item_id'], _batch)
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) + base_qty
                new_val = float(existing['total_value']) + total_cost
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute("""UPDATE stock_balances
                    SET quantity=?, total_value=?, average_cost=?, expiry_date=?
                    WHERE id=?""",
                    (new_qty, new_val, new_avg, _expiry, existing['id']))
            else:
                conn.execute(
                    """INSERT INTO stock_balances
                       (warehouse_id, item_id, batch_no, quantity, average_cost, total_value, expiry_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (inv['warehouse_id'], line['item_id'], _batch,
                     base_qty, unit_cost_base, total_cost, _expiry)
                )

            conn.execute("""
                INSERT INTO cost_layers
                (warehouse_id, item_id, batch_no, expiry_date, receipt_date,
                 original_qty, remaining_qty, unit_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv['warehouse_id'], line['item_id'],
                _batch, _expiry, inv['invoice_date'],
                base_qty, base_qty, unit_cost_base
            ))

        acc_settings = get_accounting()
        if not acc_settings.get('auto_journal_invoices', True):
            conn.execute(
                "UPDATE purchase_invoices SET status='POSTED', stock_txn_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
                (txn_id, inv_id)
            )
            conn.execute(
                "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP WHERE id=?",
                (txn_id,)
            )
            return jsonify({
                'success': True,
                'message': 'تم ترحيل الفاتورة (بدون قيد محاسبي)',
                'data': {'invoice_id': inv_id, 'stock_txn_id': txn_id, 'journal_entry_id': None}
            })

        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        user_id = get_user_id()

        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status, created_by)
               VALUES (?, ?, 'PURCHASE_INVOICE', ?, ?, ?, 'POSTED', ?)""",
            (je_no, inv['invoice_date'], inv_id, inv['invoice_no'], f"قيد فاتورة شراء {inv['invoice_no']}", user_id)
        )
        je_id = cur.lastrowid

        inv_by_account = {}
        for line in lines:
            item_info = conn.execute("SELECT inventory_account FROM items WHERE id=?", (line['item_id'],)).fetchone()
            acc = item_info['inventory_account'] if item_info else '1231'
            inv_by_account[acc] = inv_by_account.get(acc, 0) + float(line['line_subtotal'])

        line_no = 1
        td = 0
        tc = 0
        for acc, amount in inv_by_account.items():
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, ?, 'فاتورة شراء - مخزون', ?, 0)""",
                (je_id, line_no, acc, round(amount, 2))
            )
            td += amount
            line_no += 1

        if float(inv['tax_amount']) > 0:
            conn.execute(
                """INSERT INTO journal_entry_lines
                   (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
                   VALUES (?, ?, '1251', 'ضريبة مدخلات', ?, 0)""",
                (je_id, line_no, round(float(inv['tax_amount']), 2))
            )
            td += float(inv['tax_amount'])
            line_no += 1

        payment_type = inv.get('payment_type', 'CREDIT')
        payment_method_code = inv.get('payment_method_code')

        if payment_type == 'CASH':
            method_accounts = {
                'CASH':           '1211',
                'BANK_TRANSFER':  '1212',
                'CHEQUE':         '1225',
                'CARD':           '1213',
                'WALLET':         '1214',
            }
            credit_account = method_accounts.get(payment_method_code, '1211')
            credit_desc = f'نقدية - {payment_method_code or "CASH"}'
        else:
            credit_account = '1236-01'
            credit_desc = 'وسيط - استلام بضاعة'

        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (je_id, line_no, credit_account, credit_desc, round(float(inv['total_amount']), 2))
        )
        tc = float(inv['total_amount'])

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (round(td, 2), round(tc, 2), je_id))

        conn.execute(
            "UPDATE purchase_invoices SET status='POSTED', stock_txn_id=?, journal_entry_id=?, posted_at=CURRENT_TIMESTAMP WHERE id=?",
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