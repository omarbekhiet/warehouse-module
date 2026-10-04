from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

mr_bp = Blueprint('material_requests', __name__)


def _next_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM material_requests")
    return f"MR-{datetime.now().year}-{cur.fetchone()['n']:06d}"


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


@mr_bp.route('/', methods=['GET'])
def list_requests():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('status=?'); vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT mr.*, w.name_ar as warehouse_name
            FROM material_requests mr
            LEFT JOIN warehouses w ON mr.warehouse_id = w.id
            WHERE {where}
            ORDER BY mr.id DESC LIMIT 200""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@mr_bp.route('/<int:rid>', methods=['GET'])
def get_request(rid):
    r = db.query(
        """SELECT mr.*, w.name_ar as warehouse_name
           FROM material_requests mr
           LEFT JOIN warehouses w ON mr.warehouse_id = w.id
           WHERE mr.id=?""",
        (rid,), one=True
    )
    if not r:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT mrl.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name
           FROM material_request_lines mrl
           JOIN items i ON mrl.item_id = i.id
           LEFT JOIN units_of_measure u ON mrl.uom_id = u.id
           WHERE mrl.request_id=? ORDER BY mrl.line_no""",
        (rid,)
    )
    r['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(r)})


@mr_bp.route('/', methods=['POST'])
def create_request():
    d = request.get_json() or {}
    if not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_no(conn)
        cur = conn.execute(
            """INSERT INTO material_requests
               (request_no, request_date, requester_name, department,
                warehouse_id, purpose, priority, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?)""",
            (no, d.get('request_date', datetime.now().strftime('%Y-%m-%d')),
             d.get('requester_name'), d.get('department'),
             d['warehouse_id'], d.get('purpose'),
             d.get('priority', 'NORMAL'), d.get('notes'))
        )
        rid = cur.lastrowid

        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
            if base_qty is None:
                return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400

            conn.execute(
                """INSERT INTO material_request_lines
                   (request_id, line_no, item_id, uom_id, requested_qty, base_requested_qty, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (rid, i, line['item_id'], line['uom_id'],
                 float(line['quantity']), base_qty, line.get('notes'))
            )

    return jsonify({'success': True, 'data': {'id': rid, 'request_no': no}}), 201


@mr_bp.route('/<int:rid>', methods=['PUT'])
def update_request(rid):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM material_requests WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب معتمد'}), 400

        conn.execute(
            """UPDATE material_requests
               SET request_date=?, requester_name=?, department=?,
                   warehouse_id=?, purpose=?, priority=?, notes=?
               WHERE id=?""",
            (d.get('request_date'), d.get('requester_name'), d.get('department'),
             d['warehouse_id'], d.get('purpose'), d.get('priority', 'NORMAL'),
             d.get('notes'), rid)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM material_request_lines WHERE request_id=?", (rid,))
            for i, line in enumerate(d['lines'], start=1):
                factor, base_qty = _get_base_quantity(conn, line['item_id'], line['uom_id'], line['quantity'])
                if base_qty is None:
                    return jsonify({'success': False, 'message': 'الوحدة غير مرتبطة'}), 400
                conn.execute(
                    """INSERT INTO material_request_lines
                       (request_id, line_no, item_id, uom_id, requested_qty, base_requested_qty, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (rid, i, line['item_id'], line['uom_id'],
                     float(line['quantity']), base_qty, line.get('notes'))
                )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@mr_bp.route('/<int:rid>/approve', methods=['POST'])
def approve_request(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM material_requests WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row or row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن اعتماد المسودة فقط'}), 400
        conn.execute(
            "UPDATE material_requests SET status='APPROVED', approved_at=CURRENT_TIMESTAMP, approved_by=1 WHERE id=?",
            (rid,)
        )
    return jsonify({'success': True, 'message': 'تم الاعتماد'})


@mr_bp.route('/<int:rid>/reject', methods=['POST'])
def reject_request(rid):
    with db.transaction() as conn:
        conn.execute("UPDATE material_requests SET status='REJECTED' WHERE id=? AND status='DRAFT'", (rid,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@mr_bp.route('/<int:rid>/restore', methods=['POST'])
def restore_request(rid):
    with db.transaction() as conn:
        conn.execute("UPDATE material_requests SET status='DRAFT' WHERE id=? AND status='REJECTED'", (rid,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@mr_bp.route('/<int:rid>/issue', methods=['POST'])
def issue_request(rid):
    """تنفيذ الصرف - إنشاء إذن صرف + قيد محاسبي."""
    d = request.get_json() or {}
    issue_lines = d.get('lines', [])  # [{line_id, issue_qty}]
    
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM material_requests WHERE id=? AND status='APPROVED'", (rid,))
        r = cur.fetchone()
        if not r:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو غير معتمد'}), 404
        r = dict(r)

        cur = conn.execute(
            """SELECT mrl.*, i.item_type, i.inventory_account, i.cost_account, i.name_ar
               FROM material_request_lines mrl
               JOIN items i ON mrl.item_id = i.id
               WHERE mrl.request_id=?""",
            (rid,)
        )
        all_lines = [dict(x) for x in cur.fetchall()]
        
        lines = []
        for ol in all_lines:
            if issue_lines:
                il = next((l for l in issue_lines if l['line_id'] == ol['id']), None)
                if not il or float(il.get('issue_qty', 0)) <= 0:
                    continue
                qty_to_issue = float(il['issue_qty'])
            else:
                qty_to_issue = float(ol['requested_qty']) - float(ol['issued_qty'] or 0)
            
            if qty_to_issue <= 0:
                continue
            
            lines.append({**ol, 'issue_qty': qty_to_issue})
        
        if not lines:
            return jsonify({'success': False, 'message': 'لا توجد بنود للصرف'}), 400

        # Check stock availability
        for line in lines:
            cur = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (r['warehouse_id'], line['item_id'])
            )
            available = float(cur.fetchone()['q'])
            if available < float(line['issue_qty']):
                return jsonify({'success': False, 'message': f'الكمية غير كافية للصنف {line["name_ar"]}. المتاح: {available}'}), 400

        txn_no = _next_txn_no(conn, 'ISS', 'ISSUE')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by)
               VALUES (?, 'ISSUE', ?, ?, 'MATERIAL_REQUEST', ?, 'POSTED', ?, 1)""",
            (txn_no, d.get('issue_date', datetime.now().strftime('%Y-%m-%d')),
             r['warehouse_id'], r['request_no'], f"صرف بموجب طلب {r['request_no']}")
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_cost = 0

        for i, line in enumerate(lines, start=1):
            base_qty = float(line['issue_qty'])
            factor = float(line['base_requested_qty']) / float(line['requested_qty']) if float(line['requested_qty']) > 0 else 1
            base_qty_full = float(line['issue_qty']) * factor
            
            # Get avg cost
            cur = conn.execute(
                "SELECT COALESCE(SUM(total_value),0) as v, COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (r['warehouse_id'], line['item_id'])
            )
            bal = cur.fetchone()
            avg = (float(bal['v']) / float(bal['q'])) if float(bal['q']) > 0 else 0
            line_cost = base_qty_full * avg

            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 line['issue_qty'], base_qty_full, avg, line_cost)
            )

            # Deduct stock
            conn.execute(
                """UPDATE stock_balances
                   SET quantity = quantity - ?,
                       total_value = total_value - ?,
                       average_cost = CASE WHEN quantity - ? > 0
                         THEN (total_value - ?) / (quantity - ?) ELSE 0 END
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (base_qty_full, line_cost, base_qty_full, line_cost, base_qty_full,
                 r['warehouse_id'], line['item_id'])
            )

            # Update requested line
            conn.execute(
                "UPDATE material_request_lines SET issued_qty = issued_qty + ? WHERE id=?",
                (line['issue_qty'], line['id'])
            )

            total_qty += base_qty_full
            total_cost += line_cost

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_cost, 4), txn_id)
        )

        # Journal: Debit cost account, Credit inventory
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
               VALUES (?, ?, 'MATERIAL_REQUEST', ?, ?, ?, 'POSTED')""",
            (je_no, d.get('issue_date', datetime.now().strftime('%Y-%m-%d')),
             rid, r['request_no'], f"صرف بموجب طلب {r['request_no']}")
        )
        je_id = cur.lastrowid

        # Aggregate by cost account
        cost_by_account = {}
        for line in lines:
            acc = line['cost_account'] or '5563'
            factor = float(line['base_requested_qty']) / float(line['requested_qty']) if float(line['requested_qty']) > 0 else 1
            base_full = float(line['issue_qty']) * factor
            cur = conn.execute(
                "SELECT COALESCE(SUM(total_value),0) as v, COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (r['warehouse_id'], line['item_id'])
            )
            # approximate
            cost_by_account[acc] = cost_by_account.get(acc, 0) + (float(line['issue_qty']) * factor * 0)

        line_no = 1
        td = 0
        tc = 0

        # Debit expense account
        cost_acc_default = '5563'
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, ?, 'صرف - تكلفة', ?, 0)""",
            (je_id, line_no, cost_acc_default, round(total_cost, 2))
        )
        td = round(total_cost, 2)
        line_no += 1

        # Credit inventory
        inv_by_account = {}
        for line in lines:
            factor = float(line['base_requested_qty']) / float(line['requested_qty']) if float(line['requested_qty']) > 0 else 1
            base_full = float(line['issue_qty']) * factor
            cur = conn.execute(
                "SELECT COALESCE(SUM(total_value),0) as v, COALESCE(SUM(quantity),0) as q FROM stock_balances WHERE warehouse_id=? AND item_id=?",
                (r['warehouse_id'], line['item_id'])
            )
            # Use approximate cost
            inv_by_account[line['inventory_account']] = inv_by_account.get(line['inventory_account'], 0)

        # Fallback: single credit entry
        conn.execute(
            """INSERT INTO journal_entry_lines
               (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
               VALUES (?, ?, '1231', 'صرف - مخزون', 0, ?)""",
            (je_id, line_no, round(total_cost, 2))
        )
        tc = round(total_cost, 2)

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (td, tc, je_id))

        # Check if fully issued
        cur = conn.execute("SELECT SUM(requested_qty) as total, SUM(issued_qty) as issued FROM material_request_lines WHERE request_id=?", (rid,))
        rs = cur.fetchone()
        if float(rs['issued'] or 0) >= float(rs['total'] or 0):
            conn.execute("UPDATE material_requests SET status='COMPLETED', stock_txn_id=? WHERE id=?", (txn_id, rid))
        else:
            conn.execute("UPDATE material_requests SET status='PARTIAL', stock_txn_id=? WHERE id=?", (txn_id, rid))

    return jsonify({
        'success': True,
        'message': f'تم الصرف - إذن {txn_no}',
        'data': {'request_id': rid, 'stock_txn_id': txn_id, 'stock_txn_no': txn_no, 'journal_entry_id': je_id}
    })


@mr_bp.route('/<int:rid>', methods=['DELETE'])
def delete_request(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM material_requests WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row or row['status'] in ('COMPLETED', 'PARTIAL'):
            return jsonify({'success': False, 'message': 'لا يمكن حذف طلب تم صرفه'}), 400
        conn.execute("DELETE FROM material_request_lines WHERE request_id=?", (rid,))
        conn.execute("DELETE FROM material_requests WHERE id=?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
