from flask import Flask
from flask_cors import CORS

from app.routes.team3.backup_routes import backup_bp
from app.routes.auth_routes import auth_bp

app = Flask(__name__)

# Allow the Team 3 frontend to communicate with the Flask API
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5500",
                "http://localhost:5500",
            ]
        }
    },
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "DELETE", "OPTIONS"]
)

app.register_blueprint(backup_bp)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return {
        "message": "Smart Inventory Management System API is running"
    }


if __name__ == "__main__":
    app.run(debug=False)
