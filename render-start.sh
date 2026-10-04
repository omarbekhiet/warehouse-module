#!/bin/bash
echo "=========================================="
echo "  Starting Warehouse Module"
echo "=========================================="

# Create database if not exists
if [ ! -f "database/warehouse.db" ]; then
    echo "Creating database..."
    mkdir -p database
    
    # Initialize
    python scripts/init_db.py 2>/dev/null || echo "init_db skipped"
    python scripts/add_accounting.py 2>/dev/null || echo "accounting skipped"
    python scripts/add_users.py 2>/dev/null || echo "users skipped"
    python scripts/add_suppliers_groups.py 2>/dev/null || echo "suppliers_groups skipped"
    python scripts/seed_groups.py 2>/dev/null || echo "seed_groups skipped"
    python scripts/add_returns.py 2>/dev/null || echo "returns skipped"
    python scripts/add_payments.py 2>/dev/null || echo "payments skipped"
    python scripts/add_purchase_orders.py 2>/dev/null || echo "POs skipped"
    python scripts/add_material_requests.py 2>/dev/null || echo "MRs skipped"
    python scripts/add_requisitions.py 2>/dev/null || echo "REQs skipped"
    
    echo "Database created successfully!"
else
    echo "Database already exists"
fi

# Start the server
echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 "app:create_app()"