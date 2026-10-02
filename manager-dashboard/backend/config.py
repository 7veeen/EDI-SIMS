import os
from pathlib import Path
from dotenv import load_dotenv

# Try loading from manager-dashboard/backend/.env first
base_dir = Path(__file__).resolve().parent
load_dotenv(base_dir / ".env")

# Fallback to backend/.env if not yet set
main_backend_env = base_dir.parent.parent / "backend" / ".env"
if main_backend_env.exists():
    load_dotenv(main_backend_env)

# Fallback to root .env
root_env = base_dir.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "smart-inventory-management-system-super-secret-jwt-key-2026")
PORT = int(os.getenv("PORT", 5001))
DEBUG = os.getenv("FLASK_ENV", "development") == "development"
