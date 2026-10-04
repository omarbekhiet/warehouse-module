from flask import Flask, jsonify
from flask_cors import CORS

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config['SECRET_KEY'] = 'dev-secret-key'
    CORS(app)

    from app.routes.warehouse_routes import warehouse_bp
    from app.routes.item_routes import item_bp
    from app.routes.receipt_routes import receipt_bp
    from app.routes.issue_routes import issue_bp
    from app.routes.transfer_routes import transfer_bp
    from app.routes.count_routes import count_bp
    from app.routes.report_routes import report_bp
    from app.routes.uom_routes import uom_bp
    from app.routes.uom_conversion_routes import conv_bp
    from app.routes.txn_edit_routes import txn_edit_bp
    from app.routes.tier_routes import tier_bp
    from app.routes.supplier_routes import supplier_bp
    from app.routes.group_routes import group_bp
    from app.routes.purchase_invoice_routes import invoice_bp
    from app.routes.clearing_routes import clearing_bp
    from app.routes.customer_routes import customer_bp
    from app.routes.sales_invoice_routes import sales_bp
    from app.routes.account_routes import account_bp
    from app.routes.purchase_return_routes import pr_bp
    from app.routes.sales_return_routes import sr_bp
    from app.routes.payment_routes import pay_bp
    from app.routes.financial_report_routes import fin_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.export_routes import export_bp
    from app.routes.notification_routes import notif_bp
    from app.routes.purchase_order_routes import po_bp
    from app.routes.material_request_routes import mr_bp
    from app.routes.requisition_routes import req_bp

    app.register_blueprint(warehouse_bp, url_prefix='/api/v1/warehouses')
    app.register_blueprint(item_bp, url_prefix='/api/v1/items')
    app.register_blueprint(receipt_bp, url_prefix='/api/v1/receipts')
    app.register_blueprint(issue_bp, url_prefix='/api/v1/issues')
    app.register_blueprint(transfer_bp, url_prefix='/api/v1/transfers')
    app.register_blueprint(count_bp, url_prefix='/api/v1/counts')
    app.register_blueprint(report_bp, url_prefix='/api/v1/reports')
    app.register_blueprint(uom_bp, url_prefix='/api/v1/uom')
    app.register_blueprint(conv_bp, url_prefix='/api/v1/conversions')
    app.register_blueprint(txn_edit_bp, url_prefix='/api/v1/txn')
    app.register_blueprint(tier_bp, url_prefix='/api/v1/tiers')
    app.register_blueprint(supplier_bp, url_prefix='/api/v1/suppliers')
    app.register_blueprint(group_bp, url_prefix='/api/v1/groups')
    app.register_blueprint(invoice_bp, url_prefix='/api/v1/purchase-invoices')
    app.register_blueprint(clearing_bp, url_prefix='/api/v1/clearing')
    app.register_blueprint(customer_bp, url_prefix='/api/v1/customers')
    app.register_blueprint(sales_bp, url_prefix='/api/v1/sales-invoices')
    app.register_blueprint(account_bp, url_prefix='/api/v1/accounts')
    app.register_blueprint(pr_bp, url_prefix='/api/v1/purchase-returns')
    app.register_blueprint(sr_bp, url_prefix='/api/v1/sales-returns')
    app.register_blueprint(pay_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(fin_bp, url_prefix='/api/v1/financial-reports')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(export_bp, url_prefix='/api/v1/export')
    app.register_blueprint(notif_bp, url_prefix='/api/v1/notifications')
    app.register_blueprint(po_bp, url_prefix='/api/v1/purchase-orders')
    app.register_blueprint(mr_bp, url_prefix='/api/v1/material-requests')
    app.register_blueprint(req_bp, url_prefix='/api/v1/requisitions')

    @app.route('/health')
    def health():
        return {'status': 'OK'}

    @app.route('/dashboard')
    def dashboard():
        return app.send_static_file('index.html')

    @app.route('/login')
    def login_page():
        return app.send_static_file('login.html')

    @app.route('/')
    def index():
        return app.send_static_file('login.html')

    return app
