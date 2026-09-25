import logging
from typing import Optional
from supabase import create_client, Client
from .config import Config

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Returns the singleton Supabase client instance.
    If credentials are missing or invalid, logs a warning and returns None.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not Config.is_supabase_configured():
        logger.warning(
            "Supabase credentials (SUPABASE_URL and SUPABASE_KEY) are not fully configured in .env. "
            "Please configure them to connect to your live Supabase database."
        )
        return None

    try:
        _supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        logger.info("Successfully initialized Supabase client connection.")
        return _supabase_client
    except Exception as e:
        logger.warning(f"Supabase REST client initialization note: {e}. Will use direct PostgreSQL connection.")
        return None

def get_db_connection():
    """
    Returns a direct psycopg2 connection to the Supabase PostgreSQL database via DATABASE_URL.
    """
    if not Config.DATABASE_URL:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(Config.DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Supabase PostgreSQL via DATABASE_URL: {e}")
        return None
