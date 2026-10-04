from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

notif_bp = Blueprint('notifications', __name__)


@notif_bp.route('/summary', methods=['GET'])
def summary():
    """ملخص كل الإشعارات المعلقة."""
    with db.get_connection() as conn:
        # 1. فواتير شراء مسودة
        cur = conn.execute("SELECT COUNT(*) as n, COALESCE(SUM(total_amount),0) as v FROM purchase_invoices WHERE status='DRAFT'")
        pi_draft = cur.fetchone()

        # 2. فواتير شراء مرفوضة
        cur = conn.execute("SELECT COUNT(*) as n FROM purchase_invoices WHERE status='REJECTED'")
        pi_rejected = cur.fetchone()['n']

        # 3. فواتير بيع مسودة
        cur = conn.execute("SELECT COUNT(*) as n, COALESCE(SUM(total_amount),0) as v FROM sales_invoices WHERE status='DRAFT'")
        si_draft = cur.fetchone()

        # 4. فواتير بيع مرفوضة
        cur = conn.execute("SELECT COUNT(*) as n FROM sales_invoices WHERE status='REJECTED'")
        si_rejected = cur.fetchone()['n']

        # 5. أصناف تحت الحد الأدنى
        cur = conn.execute("""
            SELECT COUNT(*) as n FROM (
                SELECT i.id FROM items i
                LEFT JOIN stock_balances sb ON i.id = sb.item_id
                WHERE i.is_active=1 AND i.reorder_level > 0
                GROUP BY i.id
                HAVING COALESCE(SUM(sb.quantity),0) < i.reorder_level
            )
        """)
        low_stock = cur.fetchone()['n']

        # 6. استلامات بدون فاتورة (GRNI)
        cur = conn.execute("""
            SELECT COUNT(*) as n, COALESCE(SUM(t.total_value),0) as v
            FROM stock_transactions t
            WHERE t.transaction_type='RECEIPT'
              AND t.status='POSTED'
              AND (t.invoice_id IS NULL OR t.invoice_id = 0)
        """)
        grni = cur.fetchone()

        # 7. جرد لم يُرحّل
        cur = conn.execute("SELECT COUNT(*) as n FROM inventory_counts WHERE status IN ('DRAFT','IN_PROGRESS')")
        counts_draft = cur.fetchone()['n']

        # 8. تحويلات مسودة
        cur = conn.execute("SELECT COUNT(*) as n FROM stock_transactions WHERE transaction_type='TRANSFER' AND status='DRAFT'")
        transfers_draft = cur.fetchone()['n']

        # 9. صرف مسودة
        cur = conn.execute("SELECT COUNT(*) as n FROM stock_transactions WHERE transaction_type='ISSUE' AND status='DRAFT'")
        issues_draft = cur.fetchone()['n']

        # 10. فواتير شراء قاربت على الاستحقاق (30-60 يوم)
        cur = conn.execute("""
            SELECT COUNT(*) as n, COALESCE(SUM(total_amount),0) as v
            FROM purchase_invoices
            WHERE status='POSTED'
              AND CAST(julianday('now') - julianday(invoice_date) AS INTEGER) > 30
        """)
        pi_overdue = cur.fetchone()

        # 11. فواتير بيع لم تُحصّل (30-60 يوم)
        cur = conn.execute("""
            SELECT COUNT(*) as n, COALESCE(SUM(total_amount),0) as v
            FROM sales_invoices
            WHERE status='POSTED'
              AND CAST(julianday('now') - julianday(invoice_date) AS INTEGER) > 30
        """)
        si_overdue = cur.fetchone()

    items = [
        {
            'type': 'PI_DRAFT',
            'severity': 'warning',
            'icon': 'receipt',
            'title': 'فواتير شراء مسودة',
            'message': f'{pi_draft["n"]} فاتورة شراء لم تُرحّل',
            'count': pi_draft['n'],
            'value': float(pi_draft['v'] or 0),
            'url': '/purchase_invoices.html?status=DRAFT'
        },
        {
            'type': 'SI_DRAFT',
            'severity': 'warning',
            'icon': 'cart-check',
            'title': 'فواتير بيع مسودة',
            'message': f'{si_draft["n"]} فاتورة بيع لم تُرحّل',
            'count': si_draft['n'],
            'value': float(si_draft['v'] or 0),
            'url': '/sales_invoices.html?status=DRAFT'
        },
        {
            'type': 'LOW_STOCK',
            'severity': 'danger',
            'icon': 'exclamation-triangle',
            'title': 'أصناف تحت الحد الأدنى',
            'message': f'{low_stock} صنف يحتاج إعادة طلب',
            'count': low_stock,
            'value': 0,
            'url': '/reports.html'
        },
        {
            'type': 'GRNI',
            'severity': 'warning',
            'icon': 'box-arrow-in-down',
            'title': 'بضاعة مستلمة بدون فاتورة',
            'message': f'{grni["n"]} استلام بانتظار الفاتورة',
            'count': grni['n'],
            'value': float(grni['v'] or 0),
            'url': '/clearing.html'
        },
        {
            'type': 'COUNTS_DRAFT',
            'severity': 'info',
            'icon': 'clipboard-check',
            'title': 'جرد لم يُرحّل',
            'message': f'{counts_draft} جرد معلّق',
            'count': counts_draft,
            'value': 0,
            'url': '/counts.html'
        },
        {
            'type': 'TRANSFERS_DRAFT',
            'severity': 'info',
            'icon': 'arrow-left-right',
            'title': 'تحويلات مسودة',
            'message': f'{transfers_draft} تحويل لم يُرحّل',
            'count': transfers_draft,
            'value': 0,
            'url': '/transfers.html'
        },
        {
            'type': 'ISSUES_DRAFT',
            'severity': 'info',
            'icon': 'arrow-up-circle',
            'title': 'إذون صرف مسودة',
            'message': f'{issues_draft} إذن صرف معلّق',
            'count': issues_draft,
            'value': 0,
            'url': '/issues.html'
        },
        {
            'type': 'PI_OVERDUE',
            'severity': 'danger',
            'icon': 'clock-history',
            'title': 'فواتير شراء متأخرة السداد',
            'message': f'{pi_overdue["n"]} فاتورة تجاوزت 30 يوم',
            'count': pi_overdue['n'],
            'value': float(pi_overdue['v'] or 0),
            'url': '/payments.html'
        },
        {
            'type': 'SI_OVERDUE',
            'severity': 'danger',
            'icon': 'clock-history',
            'title': 'فواتير بيع لم تُحصّل',
            'message': f'{si_overdue["n"]} فاتورة تجاوزت 30 يوم',
            'count': si_overdue['n'],
            'value': float(si_overdue['v'] or 0),
            'url': '/customer_receipts.html'
        },
        {
            'type': 'PI_REJECTED',
            'severity': 'secondary',
            'icon': 'x-circle',
            'title': 'فواتير شراء مرفوضة',
            'message': f'{pi_rejected} فاتورة مرفوضة',
            'count': pi_rejected,
            'value': 0,
            'url': '/purchase_invoices.html?status=REJECTED'
        },
        {
            'type': 'SI_REJECTED',
            'severity': 'secondary',
            'icon': 'x-circle',
            'title': 'فواتير بيع مرفوضة',
            'message': f'{si_rejected} فاتورة مرفوضة',
            'count': si_rejected,
            'value': 0,
            'url': '/sales_invoices.html?status=REJECTED'
        },
    ]

    # Filter out empty
    items = [i for i in items if i['count'] > 0]

    total_alerts = sum(i['count'] for i in items)

    return jsonify({
        'success': True,
        'data': items,
        'total_alerts': total_alerts,
        'has_alerts': total_alerts > 0
    })


@notif_bp.route('/low-stock', methods=['GET'])
def low_stock_details():
    """تفاصيل الأصناف تحت الحد الأدنى."""
    rows = db.query("""
        SELECT i.code, i.name_ar, i.reorder_level, i.reorder_qty,
               COALESCE(SUM(sb.quantity), 0) as current_qty,
               (i.reorder_level - COALESCE(SUM(sb.quantity), 0)) as shortage
        FROM items i
        LEFT JOIN stock_balances sb ON i.id = sb.item_id
        WHERE i.is_active = 1 AND i.reorder_level > 0
        GROUP BY i.id
        HAVING current_qty < i.reorder_level
        ORDER BY shortage DESC
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})
