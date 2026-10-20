"""
محرك حساب التكلفة حسب السياسة المخزنية
يدعم: WEIGHTED_AVERAGE, FIFO, LIFO, STANDARD
"""
from app.database import db


class CostEngine:

    # ============================================================
    # جيب السياسة الفعلية للصنف
    # ============================================================
    def get_cost_method(self, item_id):
        """
        السياسة الفعلية للصنف
        الأولوية:
          1. items.cost_method
          2. item_groups.default_cost_method
          3. settings['inventory']['default_cost_method'] ← جديد
          4. WEIGHTED_AVERAGE (افتراضي)
        """
        from app.services.settings_service import get_default_cost_method
        
        item = db.query(
            "SELECT cost_method, group_id FROM items WHERE id=?",
            (item_id,), one=True
        )
        if not item:
            # ما لقيناش الصنف — نرجع للسياسة العامة
            return get_default_cost_method()
        
        # 1. سياسة الصنف
        if item['cost_method']:
            return item['cost_method']
        
        # 2. سياسة المجموعة
        if item['group_id']:
            grp = db.query(
                "SELECT default_cost_method FROM item_groups WHERE id=?",
                (item['group_id'],), one=True
            )
            if grp and grp['default_cost_method']:
                return grp['default_cost_method']
        
        # 3. السياسة العامة من الإعدادات
        return get_default_cost_method()

    def get_cost_method_with_source(self, item_id):
        """
        نفس get_cost_method لكن مع تحديد المصدر
        Returns: dict {'method': ..., 'source': 'item'|'group'|'settings'|'default'}
        """
        from app.services.settings_service import get_default_cost_method, get_inventory
        
        item = db.query(
            "SELECT cost_method, group_id FROM items WHERE id=?",
            (item_id,), one=True
        )
        if not item:
            return {'method': get_default_cost_method(), 'source': 'settings'}
        
        # 1. سياسة الصنف
        if item['cost_method']:
            return {'method': item['cost_method'], 'source': 'item'}
        
        # 2. سياسة المجموعة
        if item['group_id']:
            grp = db.query(
                "SELECT default_cost_method FROM item_groups WHERE id=?",
                (item['group_id'],), one=True
            )
            if grp and grp['default_cost_method']:
                return {'method': grp['default_cost_method'], 'source': 'group'}
        
        # 3. السياسة العامة
        inv = get_inventory()
        if inv.get('default_cost_method'):
            return {'method': inv['default_cost_method'], 'source': 'settings'}
        
        return {'method': 'WEIGHTED_AVERAGE', 'source': 'default'}

    # ============================================================
    # حساب تكلفة الصرف (حالي)
    # ============================================================
    def calculate_issue_cost(self, conn, warehouse_id, item_id, qty_to_issue):
        method = self.get_cost_method(item_id)
        
        if method == 'FIFO':
            return self._calc_fifo(conn, warehouse_id, item_id, qty_to_issue)
        elif method == 'LIFO':
            return self._calc_lifo(conn, warehouse_id, item_id, qty_to_issue)
        else:
            return self._calc_weighted_average(conn, warehouse_id, item_id, qty_to_issue)

    # ============================================================
    # ✅ دالة جديدة: حساب تاريخي (لكارت الصنف)
    # ============================================================
    def calculate_issue_cost_at_time(self, warehouse_id, item_id, qty, 
                                      up_to_date, up_to_id):
        """
        يحسب تكلفة الصرف اعتماداً على الدفعات المتاحة *حتى* تاريخ/حركة معينة
        
        Args:
            warehouse_id: المستودع
            item_id: الصنف
            qty: الكمية
            up_to_date: التاريخ (inclusive)
            up_to_id: ID الحركة (inclusive)
        
        Returns:
            dict: {unit_cost, total_cost, method, batches_used}
        """
        method = self.get_cost_method(item_id)
        
        if qty <= 0:
            return {'unit_cost': 0, 'total_cost': 0, 'method': method, 'batches_used': []}
        
        if method == 'FIFO':
            batches = db.query("""
                SELECT id, batch_no, receipt_date, quantity_remaining, unit_cost
                FROM stock_batches
                WHERE warehouse_id=? AND item_id=? AND quantity_remaining > 0
                  AND (receipt_date < ? OR (receipt_date = ? AND id <= ?))
                ORDER BY receipt_date ASC, id ASC
            """, (warehouse_id, item_id, up_to_date, up_to_date, up_to_id))
            
            return self._consume_batches_for_history(batches, qty, 'FIFO')
        
        elif method == 'LIFO':
            batches = db.query("""
                SELECT id, batch_no, receipt_date, quantity_remaining, unit_cost
                FROM stock_batches
                WHERE warehouse_id=? AND item_id=? AND quantity_remaining > 0
                  AND (receipt_date < ? OR (receipt_date = ? AND id <= ?))
                ORDER BY receipt_date DESC, id DESC
            """, (warehouse_id, item_id, up_to_date, up_to_date, up_to_id))
            
            return self._consume_batches_for_history(batches, qty, 'LIFO')
        
        else:
            # المتوسط المرجح — من الدفعات المتاحة
            result = db.query("""
                SELECT 
                    SUM(quantity_remaining) as qty,
                    SUM(quantity_remaining * unit_cost) as value
                FROM stock_batches
                WHERE warehouse_id=? AND item_id=? AND quantity_remaining > 0
                  AND (receipt_date < ? OR (receipt_date = ? AND id <= ?))
            """, (warehouse_id, item_id, up_to_date, up_to_date, up_to_id), one=True)
            
            if result and result['qty'] and float(result['qty']) > 0:
                unit_cost = float(result['value']) / float(result['qty'])
            else:
                unit_cost = 0
            
            return {
                'unit_cost': round(unit_cost, 4),
                'total_cost': round(qty * unit_cost, 2),
                'method': 'WEIGHTED_AVERAGE',
                'batches_used': []
            }

    # ============================================================
    # استهلاك الدفعات (تاريخي)
    # ============================================================
    def _consume_batches_for_history(self, batches, qty_to_issue, method):
        if not batches:
            return {
                'unit_cost': 0,
                'total_cost': 0,
                'method': method,
                'batches_used': []
            }
        
        remaining = float(qty_to_issue)
        total_cost = 0
        used_batches = []
        
        for b in batches:
            if remaining <= 0:
                break
            
            available = float(b['quantity_remaining'])
            if available <= 0:
                continue
            
            take = min(remaining, available)
            cost = take * float(b['unit_cost'])
            
            used_batches.append({
                'batch_id': b['id'],
                'batch_no': b['batch_no'] or f"B{b['id']}",
                'receipt_date': b['receipt_date'],
                'quantity': round(take, 4),
                'unit_cost': round(float(b['unit_cost']), 4),
                'total_cost': round(cost, 2)
            })
            
            total_cost += cost
            remaining -= take
        
        unit_cost = total_cost / qty_to_issue if qty_to_issue > 0 else 0
        
        return {
            'unit_cost': round(unit_cost, 4),
            'total_cost': round(total_cost, 2),
            'method': method,
            'batches_used': used_batches
        }

    # ============================================================
    # المتوسط المرجح (حالي)
    # ============================================================
    def _calc_weighted_average(self, conn, warehouse_id, item_id, qty_to_issue):
        bal = conn.execute("""
            SELECT quantity, average_cost, total_value
            FROM stock_balances
            WHERE warehouse_id=? AND item_id=? AND batch_no=''
        """, (warehouse_id, item_id)).fetchone()
        
        if not bal:
            return {'success': False, 'message': f'لا يوجد رصيد'}
        
        unit_cost = float(bal['average_cost'] or 0)
        total_cost = round(qty_to_issue * unit_cost, 2)
        
        return {
            'success': True,
            'unit_cost': round(unit_cost, 4),
            'total_cost': total_cost,
            'method': 'WEIGHTED_AVERAGE',
            'batches_used': []
        }

    # ============================================================
    # FIFO (حالي)
    # ============================================================
    def _calc_fifo(self, conn, warehouse_id, item_id, qty_to_issue):
        batches = conn.execute("""
            SELECT id, batch_no, receipt_date, quantity_remaining, unit_cost
            FROM stock_batches
            WHERE warehouse_id=? AND item_id=? AND quantity_remaining > 0
            ORDER BY receipt_date ASC, id ASC
        """, (warehouse_id, item_id)).fetchall()
        
        result = self._consume_batches_for_history(batches, qty_to_issue, 'FIFO')
        result['success'] = True
        return result

    # ============================================================
    # LIFO (حالي)
    # ============================================================
    def _calc_lifo(self, conn, warehouse_id, item_id, qty_to_issue):
        batches = conn.execute("""
            SELECT id, batch_no, receipt_date, quantity_remaining, unit_cost
            FROM stock_batches
            WHERE warehouse_id=? AND item_id=? AND quantity_remaining > 0
            ORDER BY receipt_date DESC, id DESC
        """, (warehouse_id, item_id)).fetchall()
        
        result = self._consume_batches_for_history(batches, qty_to_issue, 'LIFO')
        result['success'] = True
        return result

    # ============================================================
    # خصم/إرجاع الدفعات (للترحيل)
    # ============================================================
    def consume_batches_in_db(self, conn, batches_used):
        for b in batches_used:
            if 'batch_id' in b:
                conn.execute("""
                    UPDATE stock_batches
                    SET quantity_remaining = quantity_remaining - ?
                    WHERE id = ?
                """, (b['quantity'], b['batch_id']))

    def restore_batches_in_db(self, conn, batches_used):
        for b in batches_used:
            if 'batch_id' in b:
                conn.execute("""
                    UPDATE stock_batches
                    SET quantity_remaining = quantity_remaining + ?
                    WHERE id = ?
                """, (b['quantity'], b['batch_id']))


cost_engine = CostEngine()

