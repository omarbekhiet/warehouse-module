from app.utils import to_decimal, round_decimal


class InsufficientStockError(Exception):
    pass


class ValuationService:

    def weighted_average(self, conn, warehouse_id, item_id, quantity):
        cur = conn.execute(
            """SELECT quantity, average_cost, total_value FROM stock_balances
               WHERE warehouse_id=? AND item_id=?""",
            (warehouse_id, item_id)
        )
        row = cur.fetchone()
        unit_cost = to_decimal(row['average_cost'] if row else 0)
        total_cost = round_decimal(to_decimal(quantity) * unit_cost)
        return {
            'unit_cost': float(unit_cost),
            'total_cost': float(total_cost),
            'method': 'WEIGHTED_AVERAGE'
        }

    def fifo(self, conn, warehouse_id, item_id, quantity):
        return self._consume(conn, warehouse_id, item_id, quantity, 'ASC')

    def lifo(self, conn, warehouse_id, item_id, quantity):
        return self._consume(conn, warehouse_id, item_id, quantity, 'DESC')

    def _consume(self, conn, warehouse_id, item_id, quantity, order):
        cur = conn.execute(
            f"""SELECT id, remaining_qty, unit_cost
                FROM cost_layers
                WHERE warehouse_id=? AND item_id=? AND remaining_qty > 0
                ORDER BY receipt_date {order}, id {order}""",
            (warehouse_id, item_id)
        )
        layers = [dict(r) for r in cur.fetchall()]

        remaining = to_decimal(quantity)
        total_cost = to_decimal(0)
        consumed = []

        for l in layers:
            if remaining <= 0:
                break
            take = min(to_decimal(l['remaining_qty']), remaining)
            cost = take * to_decimal(l['unit_cost'])
            total_cost += cost
            remaining -= take
            consumed.append({
                'layer_id': l['id'],
                'qty': float(take),
                'unit_cost': float(l['unit_cost'])
            })

        if remaining > 0:
            raise InsufficientStockError(
                f'الكمية غير كافية في طبقات التكلفة'
            )

        return {
            'unit_cost': float(round_decimal(total_cost / to_decimal(quantity), 6)),
            'total_cost': float(round_decimal(total_cost)),
            'method': 'FIFO' if order == 'ASC' else 'LIFO',
            'consumed_layers': consumed
        }

    def calculate(self, conn, warehouse_id, item_id, quantity, method):
        if method == 'FIFO':
            return self.fifo(conn, warehouse_id, item_id, quantity)
        if method == 'LIFO':
            return self.lifo(conn, warehouse_id, item_id, quantity)
        return self.weighted_average(conn, warehouse_id, item_id, quantity)

    def consume_layers(self, conn, consumed):
        for l in consumed:
            conn.execute(
                "UPDATE cost_layers SET remaining_qty = remaining_qty - ? WHERE id=?",
                (l['qty'], l['layer_id'])
            )


valuation_service = ValuationService()
