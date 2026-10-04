from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from datetime import datetime

req_bp = Blueprint('requisitions', __name__)


def _next_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM purchase_requisitions")
    return f"REQ-{datetime.now().year}-{cur.fetchone()['n']:06d}"


def _next_po_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM purchase_orders")
    return f"PO-{datetime.now().year}-{cur.fetchone()['n']:06d}"


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


@req_bp.route('/', methods=['GET'])
def list_reqs():
    cond, vals = ['1=1'], []
    if request.args.get('status'):
        cond.append('status=?'); vals.append(request.args.get('status'))
    where = ' AND '.join(cond)
    rows = db.query(
        f"""SELECT pr.*, w.name_ar as warehouse_name
            FROM purchase_requisitions pr
            LEFT JOIN warehouses w ON pr.warehouse_id = w.id
            WHERE {where}
            ORDER BY pr.id DESC LIMIT 200""",
        vals
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@req_bp.route('/<int:rid>', methods=['GET'])
def get_req(rid):
    r = db.query(
        """SELECT pr.*, w.name_ar as warehouse_name
           FROM purchase_requisitions pr
           LEFT JOIN warehouses w ON pr.warehouse_id = w.id
           WHERE pr.id=?""",
        (rid,), one=True
    )
    if not r:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT prl.*, i.code as item_code, i.name_ar as item_name,
                  u.name_ar as uom_name
           FROM purchase_requisition_lines prl
           LEFT JOIN items i ON prl.item_id = i.id
           LEFT JOIN units_of_measure u ON prl.uom_id = u.id
           WHERE prl.req_id=? ORDER BY prl.line_no""",
        (rid,)
    )
    r['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(r)})


@req_bp.route('/', methods=['POST'])
def create_req():
    d = request.get_json() or {}
    if not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_no(conn)
        cur = conn.execute(
            """INSERT INTO purchase_requisitions
               (req_no, req_date, requester_name, department, warehouse_id,
                priority, needed_by, reason, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?)""",
            (no, d.get('req_date', datetime.now().strftime('%Y-%m-%d')),
             d.get('requester_name'), d.get('department'),
             d.get('warehouse_id'), d.get('priority', 'NORMAL'),
             d.get('needed_by'), d.get('reason'), d.get('notes'))
        )
        rid = cur.lastrowid

        for i, line in enumerate(d['lines'], start=1):
            conn.execute(
                """INSERT INTO purchase_requisition_lines
                   (req_id, line_no, item_id, item_description, uom_id, quantity, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (rid, i, line.get('item_id'), line.get('item_description'),
                 line.get('uom_id'), float(line['quantity']), line.get('notes'))
            )

    return jsonify({'success': True, 'data': {'id': rid, 'req_no': no}}), 201


@req_bp.route('/<int:rid>', methods=['PUT'])
def update_req(rid):
    d = request.get_json() or {}
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_requisitions WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'غير موجود'}), 404
        if row['status'] not in ('DRAFT', 'REJECTED'):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب معتمد أو محوّل'}), 400

        conn.execute(
            """UPDATE purchase_requisitions
               SET req_date=?, requester_name=?, department=?, warehouse_id=?,
                   priority=?, needed_by=?, reason=?, notes=?
               WHERE id=?""",
            (d.get('req_date'), d.get('requester_name'), d.get('department'),
             d.get('warehouse_id'), d.get('priority', 'NORMAL'),
             d.get('needed_by'), d.get('reason'), d.get('notes'), rid)
        )

        if d.get('lines'):
            conn.execute("DELETE FROM purchase_requisition_lines WHERE req_id=?", (rid,))
            for i, line in enumerate(d['lines'], start=1):
                conn.execute(
                    """INSERT INTO purchase_requisition_lines
                       (req_id, line_no, item_id, item_description, uom_id, quantity, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (rid, i, line.get('item_id'), line.get('item_description'),
                     line.get('uom_id'), float(line['quantity']), line.get('notes'))
                )

    return jsonify({'success': True, 'message': 'تم التحديث'})


@req_bp.route('/<int:rid>/approve', methods=['POST'])
def approve_req(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_requisitions WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row or row['status'] != 'DRAFT':
            return jsonify({'success': False, 'message': 'يمكن اعتماد المسودة فقط'}), 400
        conn.execute(
            "UPDATE purchase_requisitions SET status='APPROVED', approved_at=CURRENT_TIMESTAMP, approved_by=1 WHERE id=?",
            (rid,)
        )
    return jsonify({'success': True, 'message': 'تم الاعتماد'})


@req_bp.route('/<int:rid>/reject', methods=['POST'])
def reject_req(rid):
    with db.transaction() as conn:
        conn.execute("UPDATE purchase_requisitions SET status='REJECTED' WHERE id=? AND status='DRAFT'", (rid,))
    return jsonify({'success': True, 'message': 'تم الرفض'})


@req_bp.route('/<int:rid>/restore', methods=['POST'])
def restore_req(rid):
    with db.transaction() as conn:
        conn.execute("UPDATE purchase_requisitions SET status='DRAFT' WHERE id=? AND status='REJECTED'", (rid,))
    return jsonify({'success': True, 'message': 'تمت الاستعادة'})


@req_bp.route('/<int:rid>/convert-to-po', methods=['POST'])
def convert_to_po(rid):
    """تحويل طلب الاحتياج إلى أمر شراء."""
    d = request.get_json() or {}
    
    with db.transaction() as conn:
        cur = conn.execute("SELECT * FROM purchase_requisitions WHERE id=? AND status='APPROVED'", (rid,))
        r = cur.fetchone()
        if not r:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو غير معتمد'}), 404
        r = dict(r)

        if not d.get('supplier_id'):
            return jsonify({'success': False, 'message': 'يجب اختيار المورد'}), 400

        cur = conn.execute("SELECT * FROM purchase_requisition_lines WHERE req_id=? ORDER BY line_no", (rid,))
        req_lines = [dict(x) for x in cur.fetchall()]

        if not req_lines:
            return jsonify({'success': False, 'message': 'لا توجد بنود'}), 400

        # Create PO
        po_no = _next_po_no(conn)
        tax_rate = float(d.get('tax_rate', 14))
        warehouse_id = d.get('warehouse_id') or r['warehouse_id']
        
        cur = conn.execute(
            """INSERT INTO purchase_orders
               (po_no, po_date, supplier_id, warehouse_id, expected_date,
                tax_rate, status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, 1)""",
            (po_no, d.get('po_date', datetime.now().strftime('%Y-%m-%d')),
             d['supplier_id'], warehouse_id, d.get('expected_date'),
             tax_rate, f"من طلب احتياج {r['req_no']}")
        )
        po_id = cur.lastrowid

        subtotal = 0
        tax_total = 0

        for i, line in enumerate(req_lines, start=1):
            if not line.get('item_id'):
                # Try to find item by description or skip
                continue
            uom_id = line.get('uom_id') or 1
            price = float(d.get('prices', {}).get(str(line['id']), 0))
            if price == 0:
                price = float(d.get('prices', {}).get(line['id'], 0))
            
            factor, base_qty = _get_base_quantity(conn, line['item_id'], uom_id, line['quantity'])
            if base_qty is None:
                base_qty = float(line['quantity'])
            
            line_sub = float(line['quantity']) * price
            line_tax = line_sub * tax_rate / 100

            conn.execute(
                """INSERT INTO purchase_order_lines
                   (po_id, line_no, item_id, uom_id, quantity, base_quantity,
                    unit_price, discount_pct, tax_rate, line_subtotal, line_tax, line_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                (po_id, i, line['item_id'], uom_id,
                 float(line['quantity']), base_qty,
                 price, tax_rate, line_sub, line_tax, line_sub + line_tax)
            )

            subtotal += line_sub
            tax_total += line_tax

        conn.execute(
            "UPDATE purchase_orders SET subtotal=?, tax_amount=?, total_amount=? WHERE id=?",
            (round(subtotal, 2), round(tax_total, 2), round(subtotal+tax_total, 2), po_id)
        )

        conn.execute(
            "UPDATE purchase_requisitions SET status='CONVERTED', purchase_order_id=? WHERE id=?",
            (po_id, rid)
        )

    return jsonify({
        'success': True,
        'message': f'تم التحويل إلى أمر شراء {po_no}',
        'data': {'po_id': po_id, 'po_no': po_no}
    })


@req_bp.route('/<int:rid>', methods=['DELETE'])
def delete_req(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT status FROM purchase_requisitions WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row or row['status'] == 'CONVERTED':
            return jsonify({'success': False, 'message': 'لا يمكن حذف طلب محوّل'}), 400
        conn.execute("DELETE FROM purchase_requisition_lines WHERE req_id=?", (rid,))
        conn.execute("DELETE FROM purchase_requisitions WHERE id=?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
