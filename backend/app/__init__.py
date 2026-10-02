from flask import Flask, request, make_response
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from app.config import JWT_SECRET_KEY
from app.routes.team1.auth import auth_bp
from app.routes.team1.users import users_bp
from app.routes.team1.categories import categories_bp
from app.routes.team1.products import products_bp
from app.routes.team2.purchase_orders import po_bp
from app.routes.team2.quotations import quotations_bp
from app.routes.team3.reports import reports_bp
from app.routes.team3.dashboard import dashboard_bp
from app.routes.team3.notifications import notifications_bp
from app.routes.team3.audit_logs import audit_logs_bp
from app.routes.team3.backups import backups_bp
from app.routes.team3.status import status_bp


def create_app():
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:8000",
                    "http://127.0.0.1:8000"
                ],
                "allow_headers": ["Content-Type", "Authorization"],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "expose_headers": ["Content-Disposition"]
            }
        }
    )

    @app.before_request
    def handle_options_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.status_code = 200
            return response

    JWTManager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(po_bp)
    app.register_blueprint(quotations_bp)

    try:
        from app.routes.team1.products import products_bp
        app.register_blueprint(products_bp)
    except (ImportError, AttributeError):
        pass

    app.register_blueprint(reports_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(audit_logs_bp)
    app.register_blueprint(backups_bp)
    app.register_blueprint(status_bp)

    return app