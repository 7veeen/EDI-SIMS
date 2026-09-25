import os
import sys
from pathlib import Path

# Add project root and backend directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app import create_app
from backend.app.config.config import Config

app = create_app()

if __name__ == "__main__":
    port = Config.PORT
    debug = Config.DEBUG
    print(f"============================================================")
    print(f"Smart Inventory Management System - Team 2 Supplier Dashboard")
    print(f"Starting server on http://localhost:{port}")
    print(f"Supplier Dashboard: http://localhost:{port}/")
    print(f"API Base URL: http://localhost:{port}/api/team2/supplier")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=debug)
