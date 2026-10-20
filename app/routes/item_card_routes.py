from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from app.services.cost_engine import cost_engine

card_bp = Blueprint('item_card', __name__)


@card_bp.route('/<int:iid>/card', methods=['GET'])
def item_card(iid):
    item = db.query("SELECT * FROM items WHERE id=?", (iid,), one=True)
    if not item:
        return jsonify({'success': False, 'message': 'الصنف غير موجود'}), 404

    item = dict(item)
    policy_info = cost_engine.get_cost_method_with_source(iid)
    item['effective_cost_method'] = policy_info['method']
    item['effective_cost_method_source'] = policy_info['source']

    source_labels = {
        'item': 'سياسة الصنف',
        'group': 'سياسة المجموعة',
        'settings': 'الإعدادات العامة',
        'default': 'افتراضي'
    }
    item['effective_cost_method_source_label'] = source_labels.get(policy_info['source'], '-')

    balances = db.query("""
        SELECT
            sb.warehouse_id,
            w.code as warehouse_code,
            w.name_ar as warehouse_name,
            SUM(sb.quantity) as quantity,
            SUM(sb.total_value) as total_value,
            CASE
                WHEN SUM(sb.quantity) > 0
                THEN SUM(sb.total_value) / SUM(sb.quantity)
                ELSE 0
            END as average_cost
        FROM stock_balances sb
        JOIN warehouses w ON sb.warehouse_id = w.id
        WHERE sb.item_id = ?
        GROUP BY sb.warehouse_id
        ORDER BY w.code
    """, (iid,))

    total_qty = sum(float(b['quantity'] or 0) for b in balances)
    total_value = sum(float(b['total_value'] or 0) for b in balances)

    pending_result = db.query("""
        SELECT COALESCE(SUM(stl.base_quantity), 0) as pending_qty
        FROM stock_transaction_lines stl
        JOIN stock_transactions st ON stl.transaction_id = st.id
        WHERE st.transaction_type = 'RECEIPT'
          AND st.status = 'POSTED'
          AND stl.item_id = ?
          AND NOT EXISTS (
              SELECT 1 FROM purchase_invoices pi
              WHERE pi.receipt_id = st.id
          )
    """, (iid,), one=True)

    pending_qty = float(pending_result['pending_qty'] or 0) if pending_result else 0
    available_qty = total_qty - pending_qty

    # ✅ الحساب: من الأقدم للأحدث (عشان الرصيد التراكمي الصح)
    movements_raw = db.query("""
        SELECT
            st.id,
            st.transaction_no,
            st.transaction_date,
            st.transaction_type,
            st.status,
            st.notes,
            st.from_warehouse_id,
            st.to_warehouse_id,
            stl.line_no,
            stl.quantity,
            stl.base_quantity,
            stl.unit_cost,
            stl.total_cost,
            u.name_ar as uom_name,
            wf.code as from_warehouse_code,
            wf.name_ar as from_warehouse_name,
            wt.code as to_warehouse_code,
            wt.name_ar as to_warehouse_name,
            pi.invoice_no,
            pi.invoice_date as invoice_date
        FROM stock_transaction_lines stl
        JOIN stock_transactions st ON stl.transaction_id = st.id
        LEFT JOIN units_of_measure u ON stl.uom_id = u.id
        LEFT JOIN warehouses wf ON st.from_warehouse_id = wf.id
        LEFT JOIN warehouses wt ON st.to_warehouse_id = wt.id
        LEFT JOIN purchase_invoices pi ON pi.receipt_id = st.id
                                       AND st.transaction_type = 'RECEIPT'
        WHERE stl.item_id = ?
          AND st.status = 'POSTED'
        ORDER BY st.transaction_date ASC, st.id ASC
    """, (iid,))

    movements_list = []
    running_qty = 0
    running_value = 0
    running_avg = 0

    for m in movements_raw:
        m = dict(m)

        base_qty = float(m['base_quantity'] or m['quantity'] or 0)
        unit_cost = float(m['unit_cost'] or 0)
        total_cost = float(m['total_cost'] or 0)

        if m['transaction_type'] == 'RECEIPT':
            if m.get('invoice_no'):
                m['movement_status'] = 'INVOICED'
                m['movement_status_label'] = 'OK'
            else:
                m['movement_status'] = 'PENDING_INVOICE'
                m['movement_status_label'] = 'PENDING'
        else:
            m['movement_status'] = m['status'] or 'DRAFT'
            m['movement_status_label'] = 'OK' if m['status'] == 'POSTED' else 'DRAFT'

        in_qty = 0; in_price = 0; in_value = 0
        out_qty = 0; out_price = 0; out_value = 0
        movement_policy = '-'

        if m['transaction_type'] == 'RECEIPT':
            m['direction'] = 'IN'
            m['direction_label'] = 'IN'
            in_qty = base_qty
            in_price = unit_cost if unit_cost > 0 else 0
            in_value = total_cost if total_cost > 0 else (in_qty * in_price)
            running_qty += base_qty
            running_value += in_value
            movement_policy = '-'

        elif m['transaction_type'] == 'ISSUE':
            m['direction'] = 'OUT'
            m['direction_label'] = 'OUT'
            out_qty = base_qty

            if unit_cost > 0:
                out_price = unit_cost
                out_value = total_cost if total_cost > 0 else (out_qty * unit_cost)
                movement_policy = 'FIFO'
            else:
                warehouse_id = m.get('from_warehouse_id')
                cost_result = None
                if warehouse_id:
                    try:
                        cost_result = cost_engine.calculate_issue_cost_at_time(
                            warehouse_id, iid, base_qty,
                            m['transaction_date'], m['id']
                        )
                    except Exception:
                        cost_result = None

                if cost_result and cost_result.get('unit_cost', 0) > 0:
                    out_price = cost_result['unit_cost']
                    out_value = cost_result['total_cost']
                    movement_policy = cost_result['method']
                else:
                    out_price = running_avg if running_avg > 0 else 0
                    out_value = out_qty * out_price
                    movement_policy = 'AVERAGE'

            running_qty -= base_qty
            running_value -= out_value

        elif m['transaction_type'] == 'TRANSFER':
            m['direction'] = 'TRANSFER'
            m['direction_label'] = 'TRANSFER'
            movement_policy = '-'

        elif m['transaction_type'] in ('ADJUSTMENT', 'COUNT_ADJUST'):
            m['direction'] = 'ADJUST'
            m['direction_label'] = 'ADJUST'
            if base_qty > 0:
                in_qty = base_qty
                in_price = unit_cost if unit_cost > 0 else running_avg
                in_value = total_cost if total_cost > 0 else (in_qty * in_price)
                running_qty += base_qty
                running_value += in_value
            else:
                out_qty = abs(base_qty)
                if unit_cost > 0:
                    out_price = unit_cost
                    out_value = total_cost if total_cost > 0 else (out_qty * unit_cost)
                else:
                    out_price = running_avg if running_avg > 0 else unit_cost
                    out_value = out_qty * out_price
                running_qty += base_qty
                running_value -= out_value
            movement_policy = 'ADJUST'

        elif m['transaction_type'] == 'WASTE':
            m['direction'] = 'OUT'
            m['direction_label'] = 'WASTE'
            out_qty = base_qty
            if unit_cost > 0:
                out_price = unit_cost
                out_value = total_cost if total_cost > 0 else (out_qty * unit_cost)
                movement_policy = 'FIFO'
            else:
                warehouse_id = m.get('from_warehouse_id')
                cost_result = None
                if warehouse_id:
                    try:
                        cost_result = cost_engine.calculate_issue_cost_at_time(
                            warehouse_id, iid, base_qty,
                            m['transaction_date'], m['id']
                        )
                    except Exception:
                        cost_result = None
                if cost_result and cost_result.get('unit_cost', 0) > 0:
                    out_price = cost_result['unit_cost']
                    out_value = cost_result['total_cost']
                    movement_policy = cost_result['method']
                else:
                    out_price = running_avg if running_avg > 0 else 0
                    out_value = out_qty * out_price
                    movement_policy = 'AVERAGE'
            running_qty -= base_qty
            running_value -= out_value

        if running_qty > 0:
            running_avg = running_value / running_qty
        else:
            running_avg = 0

        m['in_qty'] = in_qty
        m['in_price'] = in_price
        m['in_value'] = in_value
        m['out_qty'] = out_qty
        m['out_price'] = out_price
        m['out_value'] = out_value
        m['balance_qty'] = running_qty
        m['balance_value'] = running_value
        m['balance_avg'] = running_avg
        m['movement_policy'] = movement_policy

        movements_list.append(json_safe(m))

    # ✅ العرض: من الأحدث للأقدم (تنازلي)
    # movements_list.reverse()  # معطل - عشان الترتيب تصاعدي

    response = {
        'item': json_safe(item),
        'movements': movements_list,
        'summary': {
            'total_qty': total_qty,
            'available_qty': available_qty,
            'pending_qty': pending_qty,
            'total_value': total_value,
        },
        'warehouses': [json_safe(b) for b in balances],
    }

    return jsonify({'success': True, 'data': response})
