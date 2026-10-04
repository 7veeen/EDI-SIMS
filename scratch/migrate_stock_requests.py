import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

def run_migration():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Checking/creating StockRequests table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "StockRequests" (
                stock_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                request_number VARCHAR(50) UNIQUE NOT NULL,
                requested_by BIGINT NOT NULL REFERENCES "Users"(user_id),
                supplier_id BIGINT NOT NULL REFERENCES "Suppliers"(supplier_id),
                status VARCHAR(50) NOT NULL DEFAULT 'Pending',
                priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
                required_date DATE,
                notes TEXT,
                supplier_response_notes TEXT,
                responded_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        print("Checking/creating StockRequestItems table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "StockRequestItems" (
                stock_request_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                stock_request_id BIGINT NOT NULL REFERENCES "StockRequests"(stock_request_id) ON DELETE CASCADE,
                product_id BIGINT NOT NULL REFERENCES "Products"(product_id),
                requested_quantity INTEGER NOT NULL CHECK (requested_quantity > 0),
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Add indexes for efficient queries and supplier isolation
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_requests_supplier ON "StockRequests"(supplier_id);
            CREATE INDEX IF NOT EXISTS idx_stock_requests_status ON "StockRequests"(status);
            CREATE INDEX IF NOT EXISTS idx_stock_requests_requested_by ON "StockRequests"(requested_by);
            CREATE INDEX IF NOT EXISTS idx_stock_request_items_request ON "StockRequestItems"(stock_request_id);
            CREATE INDEX IF NOT EXISTS idx_stock_request_items_product ON "StockRequestItems"(product_id);
        """)

        # Check if SupplierQuotations can reference stock_request_id
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'SupplierQuotations' AND column_name = 'stock_request_id';
        """)
        if not cur.fetchone():
            print("Adding optional stock_request_id to SupplierQuotations...")
            cur.execute("""
                ALTER TABLE "SupplierQuotations"
                ADD COLUMN stock_request_id BIGINT REFERENCES "StockRequests"(stock_request_id);
            """)

        conn.commit()
        print("Migration for StockRequests completed successfully!")

    except Exception as e:
        conn.rollback()
        print("Migration failed:", e)
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
