from flask import Flask
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


def create_app():
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "*"
            }
        }
    )

    JWTManager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(po_bp)
    app.register_blueprint(quotations_bp)

    app.register_blueprint(reports_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(audit_logs_bp)
    app.register_blueprint(backups_bp)

    return app