import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from .config.config import Config
from .routes.team2.supplier_dashboard_routes import supplier_dashboard_bp
from .routes.team2.supplier_po_routes import supplier_po_bp
from .routes.team2.supplier_shipment_routes import supplier_shipment_bp

def create_app(config_class=Config) -> Flask:
    """Flask application factory."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "team2"
    
    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="/static"
    )
    app.config.from_object(config_class)

    # Enable CORS for all API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register Team 2 Blueprints
    app.register_blueprint(supplier_dashboard_bp)
    app.register_blueprint(supplier_po_bp)
    app.register_blueprint(supplier_shipment_bp)

    # Serve Supplier Dashboard Frontend at root and /team2
    @app.route("/")
    @app.route("/index.html")
    @app.route("/team2")
    @app.route("/team2/index.html")
    @app.route("/supplier-dashboard")
    @app.route("/dashboard")
    @app.route("/purchase-orders/index.html")
    def serve_supplier_dashboard():
        return send_from_directory(str(frontend_dir), "index.html")

    # Serve Purchase Orders Frontend
    @app.route("/purchase-orders")
    @app.route("/purchase-orders/")
    @app.route("/team2/purchase-orders")
    @app.route("/purchase-orders.html")
    @app.route("/team2/purchase-orders.html")
    def serve_purchase_orders():
        return send_from_directory(str(frontend_dir), "purchase-orders.html")

    # Serve Shipments Frontend
    @app.route("/shipments")
    @app.route("/shipments/")
    @app.route("/team2/shipments")
    @app.route("/shipments.html")
    @app.route("/team2/shipments.html")
    def serve_shipments():
        return send_from_directory(str(frontend_dir), "shipments.html")

    # Serve Order & Status History Frontend
    @app.route("/order-history")
    @app.route("/order-history/")
    @app.route("/history")
    @app.route("/history/")
    @app.route("/team2/order-history")
    @app.route("/order-history.html")
    @app.route("/team2/order-history.html")
    def serve_order_history():
        return send_from_directory(str(frontend_dir), "order-history.html")

    # Serve static assets from frontend/team2
    @app.route("/purchase-orders.css")
    def serve_po_css_root():
        return send_from_directory(str(frontend_dir), "purchase-orders.css")

    @app.route("/purchase-orders.js")
    def serve_po_js_root():
        return send_from_directory(str(frontend_dir), "purchase-orders.js")

    @app.route("/shipments.css")
    def serve_shipments_css_root():
        return send_from_directory(str(frontend_dir), "shipments.css")

    @app.route("/shipments.js")
    def serve_shipments_js_root():
        return send_from_directory(str(frontend_dir), "shipments.js")

    @app.route("/order-history.css")
    def serve_order_history_css_root():
        return send_from_directory(str(frontend_dir), "order-history.css")

    @app.route("/order-history.js")
    def serve_order_history_js_root():
        return send_from_directory(str(frontend_dir), "order-history.js")


    # Serve static assets from frontend/team2
    @app.route("/css/<path:path>")
    def serve_css(path):
        return send_from_directory(str(frontend_dir / "css"), path)

    @app.route("/js/<path:path>")
    def serve_js(path):
        return send_from_directory(str(frontend_dir / "js"), path)

    # API 404 Handler
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "message": "Resource not found",
            "error": "The requested API endpoint or resource was not found"
        }), 404

    # API 500 Handler
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "success": False,
            "message": "Internal Server Error",
            "error": str(e)
        }), 500

    return app
