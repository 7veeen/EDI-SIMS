import os
import psycopg2
from app.config import DATABASE_URL


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)