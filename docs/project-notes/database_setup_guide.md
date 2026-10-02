# Database Setup & Configuration Guide

This guide provides step-by-step instructions for initializing the PostgreSQL database, configuring environment variables, and restoring system tables from the automated JSON backup snapshots for the **Smart Inventory Management System (SIMS)**.

---

## 1. Prerequisites

Ensure the following runtimes and tools are installed on your host machine:
* **PostgreSQL** 14.0 or higher (with `psql` and pgAdmin)
* **Python** 3.10 or higher
* **Git**

---

## 2. PostgreSQL Instance Setup

1. Open your terminal or `psql` command prompt:
```bash
psql -U postgres
```

2. Create the project database:
```sql
CREATE DATABASE sims_db;
CREATE USER sims_user WITH ENCRYPTED PASSWORD 'sims_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sims_db TO sims_user;
```

---

## 3. Environment Configuration (`backend/.env`)

In the `backend/` directory, create or update `.env` with your database credentials and a strong secret key for signing JWT tokens:

```ini
# PostgreSQL Database Connection String
DATABASE_URL=postgresql://sims_user:sims_secure_password@localhost:5432/sims_db

# JWT Secret Key for token signing
JWT_SECRET_KEY=super-secret-jwt-key-sims-2026-secure
```

---

## 4. DDL Schema Definition (15 Tables)

Execute the following SQL script in `sims_db` to create all required tables with primary keys and foreign key constraints:

```sql
-- 1. Roles
CREATE TABLE IF NOT EXISTS public."Roles" (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- 2. Users
CREATE TABLE IF NOT EXISTS public."Users" (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT REFERENCES public."Roles"(role_id) ON DELETE RESTRICT,
    status VARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive'))
);

-- 3. Categories
CREATE TABLE IF NOT EXISTS public."Categories" (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- 4. Products
CREATE TABLE IF NOT EXISTS public."Products" (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category_id INT REFERENCES public."Categories"(category_id) ON DELETE SET NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    selling_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    reorder_level INT NOT NULL DEFAULT 10,
    status VARCHAR(20) DEFAULT 'Active'
);

-- 5. Inventory
CREATE TABLE IF NOT EXISTS public."Inventory" (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT UNIQUE REFERENCES public."Products"(product_id) ON DELETE CASCADE,
    quantity_available INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Suppliers
CREATE TABLE IF NOT EXISTS public."Suppliers" (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    status VARCHAR(20) DEFAULT 'Active'
);

-- 7. Supplier Quotations
CREATE TABLE IF NOT EXISTS public."SupplierQuotations" (
    quotation_id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES public."Suppliers"(supplier_id) ON DELETE CASCADE,
    product_id INT REFERENCES public."Products"(product_id) ON DELETE CASCADE,
    quotation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quoted_price NUMERIC(10, 2) NOT NULL,
    quantity INT NOT NULL,
    valid_until DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected'))
);

-- 8. Purchase Orders
CREATE TABLE IF NOT EXISTS public."PurchaseOrders" (
    purchase_order_id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES public."Suppliers"(supplier_id) ON DELETE RESTRICT,
    ordered_by INT REFERENCES public."Users"(user_id) ON DELETE RESTRICT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_delivery DATE,
    total_amount NUMERIC(12, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'Created' CHECK (status IN ('Created', 'Received', 'Completed'))
);

-- 9. Purchase Order Items
CREATE TABLE IF NOT EXISTS public."PurchaseOrderItems" (
    purchase_order_item_id SERIAL PRIMARY KEY,
    purchase_order_id INT REFERENCES public."PurchaseOrders"(purchase_order_id) ON DELETE CASCADE,
    product_id INT REFERENCES public."Products"(product_id) ON DELETE RESTRICT,
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL
);

-- 10. Stock Transactions
CREATE TABLE IF NOT EXISTS public."StockTransactions" (
    transaction_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES public."Products"(product_id) ON DELETE RESTRICT,
    user_id INT REFERENCES public."Users"(user_id) ON DELETE RESTRICT,
    purchase_order_id INT REFERENCES public."PurchaseOrders"(purchase_order_id) ON DELETE SET NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('STOCK_IN', 'STOCK_OUT')),
    quantity INT NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. System Status
CREATE TABLE IF NOT EXISTS public."SystemStatus" (
    status_id SERIAL PRIMARY KEY,
    module_name VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL,
    progress INT DEFAULT 100,
    message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Reports
CREATE TABLE IF NOT EXISTS public."Reports" (
    report_id SERIAL PRIMARY KEY,
    report_name VARCHAR(150) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    generated_by INT REFERENCES public."Users"(user_id) ON DELETE SET NULL,
    generated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Notifications
CREATE TABLE IF NOT EXISTS public."Notifications" (
    notification_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES public."Users"(user_id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(30) DEFAULT 'INFO',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. Audit Logs
CREATE TABLE IF NOT EXISTS public."AuditLogs" (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES public."Users"(user_id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- 15. Backup History
CREATE TABLE IF NOT EXISTS public."BackupHistory" (
    backup_id SERIAL PRIMARY KEY,
    backup_name VARCHAR(150) NOT NULL,
    backup_type VARCHAR(30) DEFAULT 'Full',
    backup_size VARCHAR(20),
    backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES public."Users"(user_id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'Success'
);
```

---

## 5. Restoring Initial Data from JSON Backup

The project maintains verified point-in-time database exports in `backend/backups/`. To populate your local database with default users (Owner, Manager, Employee, Supplier), categories, and catalog samples:

Run the following one-line Python command from the project root:

```bash
python -c "
import json, psycopg2, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
with open('backend/backups/inventory_backup_20260919_115747.json', 'r') as f:
    data = json.load(f)
for tbl in ['Roles', 'Users', 'Categories', 'Products', 'Inventory', 'Suppliers', 'SystemStatus']:
    if tbl in data:
        for row in data[tbl]:
            cols = ', '.join(['\"' + k + '\"' for k in row.keys()])
            vals = list(row.values())
            placeholders = ', '.join(['%s'] * len(vals))
            cur.execute(f'INSERT INTO public.\"{tbl}\" ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING', vals)
conn.commit()
cur.close()
conn.close()
print('Initial data restored successfully.')
"
```

---

## 6. Starting the Backend Server

1. Activate your virtual environment:
```powershell
# Windows
.\.venv\Scripts\Activate.ps1
```

2. Install any missing packages:
```bash
pip install -r backend/requirements.txt
```

3. Launch the server:
```bash
python backend/run.py
```

4. The server will start on `http://127.0.0.1:5000/`. Verify health by accessing `http://127.0.0.1:5000/api/reports/status` in your browser or Postman.

