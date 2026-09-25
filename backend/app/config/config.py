import os
from pathlib import Path
from dotenv import load_dotenv

# Locate project root and load .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    """Application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-inventory-default-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    PORT = int(os.getenv("PORT", 5000))
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
    
    # Database URL (Direct PostgreSQL connection to Supabase pooler)
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()

    @classmethod
    def is_db_configured(cls) -> bool:
        """Check if Supabase Database URL or credentials are provided."""
        return bool(cls.DATABASE_URL or (cls.SUPABASE_URL and cls.SUPABASE_KEY and not cls.SUPABASE_URL.startswith("https://your-project-id")))

    @classmethod
    def is_supabase_configured(cls) -> bool:
        """Check if Supabase credentials are provided."""
        return cls.is_db_configured()
