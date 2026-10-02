# Team Responsibilities & Engineering Workflow Matrix

This document outlines the division of responsibilities, directory ownership, Git branching policies, and coding standards across **Team 1**, **Team 2**, and **Team 3** for the Smart Inventory Management System (SIMS).

---

## 👥 Team Breakdown & Domain Ownership

```
               ┌────────────────────────────────────────────────────────┐
               │         Smart Inventory Management System (SIMS)        │
               └───────────────────────────┬────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│      TEAM 1      │             │      TEAM 2      │             │      TEAM 3      │
│ Core Foundation  │             │   Procurement    │             │   Operations &   │
│   & Identity     │             │   & Logistics    │             │    Telemetry     │
└──────────────────┘             └──────────────────┘             └──────────────────┘
```

### 🔹 Team 1: Foundation, Security & Catalog Master Data
* **Scope**: Identity lifecycle, access control, master product catalogs.
* **Assigned Directories**:
  * `backend/app/middleware/team1_auth.py`
  * `backend/app/routes/team1/` (`auth.py`, `users.py`, `categories.py`, `products.py`, `inventory.py`)
  * `backend/app/services/team1/` (`auth_service.py`, `user_service.py`, `category_service.py`, `product_service.py`, `inventory_service.py`)
  * `frontend/js/team1/`
  * `tests/team1/`
* **Key Deliverables**:
  * User authentication with password hashing (`generate_password_hash`, `check_password_hash`).
  * JWT issuance with custom role payload.
  * Role authorization middleware (`@role_required`, `verify_active_user`).
  * Category and Product management CRUD operations.

---

### 🔹 Team 2: Procurement, Suppliers & Physical Stock Logistics
* **Scope**: Supply chain relationships, purchase orders, incoming/outgoing transactions.
* **Assigned Directories**:
  * `backend/app/routes/team2/` (`suppliers.py`, `purchase_orders.py`, `quotations.py`, `transactions.py`)
  * `backend/app/services/team2/` (`supplier_service.py`, `order_service.py`, `transaction_service.py`)
  * `frontend/js/team2/`
  * `tests/team2/`
* **Key Deliverables**:
  * Supplier directory management and contact profiling.
  * Supplier quotation submissions and validity verification.
  * Purchase order generation and line item subtotal calculations.
  * Recording physical stock movements (`STOCK_IN` upon receiving goods, `STOCK_OUT` upon fulfillment).
  * Automated update of `Inventory.quantity_available`.

---

### 🔹 Team 3: Telemetry, Reporting, Auditing & Administration
* **Scope**: Operational insights, system integrity, audit trails, and automated recovery.
* **Assigned Directories**:
  * `backend/app/routes/team3/` (`dashboard.py`, `reports.py`, `notifications.py`, `audit_logs.py`, `backups.py`)
  * `backend/app/services/team3/` (`dashboard_service.py`, `report_service.py`, `backup_service.py`)
  * `backend/backups/`
  * `frontend/js/team3/` (`dashboard.js`, `reports.js`, `backups.js`, `notifications.js`, `audit-logs.js`)
  * `tests/team3/`
* **Key Deliverables**:
  * Role-specific dashboards (Employee: stock in/out, low stock; Supplier: PO value, quotations).
  * Gated report generation with concurrency check on `SystemStatus`.
  * Real-time notifications and read receipt tracking (`is_read = TRUE`).
  * Mutation audit trail logging with user IDs, tables, and IP addresses.
  * Full JSON database snapshot exports for disaster recovery.

---

## 🌿 Git Branching Strategy & Workflow

The repository adopts a feature-branch and integration-branch model:

```
[origin/master] ────────────● (Stable Releases)
                             ▲
                             │ PR Merge
[team3] ────────────────────● (Current Active Integration)
        ▲                    ▲
        │                    │ Merge
[team1-development] ─────────┘ (Team 1 Completed Features)
        │
[team2-development] ─────────> (Pending Integration)
```

### Collaboration Rules
1. **Branch Naming**: Feature branches must be named `team<N>-<feature-description>` (e.g., `team2-purchase-orders`).
2. **Commit Conventions**: Use imperative, descriptive commit messages (e.g., `Implement inventory report generation`, `integrate team1 authentication and category APIs`).
3. **No Direct Master Commits**: All changes must be merged via reviewed Pull Requests.
4. **App Factory Blueprint Isolation**: Every team must register blueprints inside `backend/app/__init__.py` using distinct URL prefixes:
   * Team 1: `/api/auth`, `/api/users`, `/api/categories`, `/api/products`
   * Team 2: `/api/suppliers`, `/api/purchase-orders`, `/api/transactions`
   * Team 3: `/api/dashboard`, `/api/reports`, `/api/notifications`, `/api/audit-logs`, `/api/backups`

---

## 📋 Coding Standards & Guidelines

* **Database Queries**:
  * NEVER concatenate parameters directly into SQL strings.
  * ALWAYS use parameterized queries with `%s` and tuples:
    ```python
    cursor.execute('SELECT * FROM "Users" WHERE username = %s', (username,))
    ```
* **Resource Cleanup**:
  * Always close database cursors and connections in a `finally` block:
    ```python
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # queries...
    finally:
        cursor.close()
        conn.close()
    ```
* **Decoupled Architecture**:
  * Route functions must only handle HTTP concerns (parsing JSON, status codes).
  * Data processing and SQL executions belong strictly inside `services/`.

