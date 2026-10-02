# Sprint Meeting Notes & Implementation Milestones

This document records team sprint milestones, architectural decisions, completed deliverables, and upcoming engineering roadmaps for the **Smart Inventory Management System (SIMS)**.

---

## 📅 Sprint Chronology & Milestones

### 🏁 Sprint 1: Project Scaffolding & Core Authentication Foundation
* **Lead Team**: Team 1
* **Focus**: Repository layout, database schema definition, JWT authentication foundation.
* **Key Achievements**:
  * Established 3-tier repository layout (`backend/`, `database/`, `frontend/`, `docs/`, `tests/`).
  * Created `app/` Application Factory with Flask Blueprints.
  * Implemented `auth_service.py` with password hashing (`generate_password_hash`, `check_password_hash`).
  * Added JWT token generation upon login.
  * Scaffolded user onboarding and role assignment.
* **Git Milestone**: Merged pull request `#1` from `mrugadni-29/team1-development` (`e362e13`).

---

### 🏁 Sprint 2: Operations, Dashboards & Automated Recovery
* **Lead Team**: Team 3
* **Focus**: Operational telemetry, status gating, disaster recovery backups, and role dashboards.
* **Key Achievements**:
  * Implemented `dashboard_service.py` with aggregation metrics for Employee and Supplier roles.
  * Created dynamic multi-table JSON database backup mechanism in `backups.py`.
  * Added `BackupHistory` tracking with human-readable file sizes (`B`, `KB`, `MB`).
  * Implemented `Notifications` system with read-status acknowledgment (`PATCH /api/notifications/<id>/read`).
  * Built security `AuditLogs` querying endpoints.
* **Git Milestone**: Commit `4c5d228` ("Implement Team 3 inventory management features").

---

### 🏁 Sprint 3: Gated Reporting & Team 1 / Team 3 Integration
* **Lead Teams**: Team 1 & Team 3
* **Focus**: Concurrency locking, report generation, RBAC middleware integration.
* **Key Achievements**:
  * Built `reports.py` with concurrency safety: queries `SystemStatus` for `'Inventory'` module before allowing report generation. Returns `423 Locked` if status is not `'READY'`.
  * Built dynamic stock health calculator (`IN STOCK` vs `LOW STOCK` when `quantity_available <= reorder_level`).
  * Integrated Team 1's `team1_auth.py` middleware (`@role_required` and `verify_active_user`) into Team 3 dashboard endpoints.
  * Completed Category CRUD endpoints (`/api/categories/`).
* **Git Milestone**: Commit `0e37259` ("integrate team1 authentication and category APIs").

---

## 🚀 Sprint 4 (Current / In-Progress): Catalog Completion & Team 2 Integration

### Sprint Objectives
1. **Team 1**:
   * Implement route endpoints in `backend/app/routes/team1/products.py` and logic in `product_service.py`.
   * Implement stock update operations in `backend/app/routes/team1/inventory.py` and `inventory_service.py`.
2. **Team 2**:
   * Implement Supplier routes (`routes/team2/suppliers.py`) and Quotation handling.
   * Implement Purchase Order line item workflows (`PurchaseOrders` and `PurchaseOrderItems`).
   * Implement physical transaction entries (`StockTransactions` for `STOCK_IN` and `STOCK_OUT`).
3. **Team 3 / Frontend**:
   * Wire client-side JavaScript controllers in `frontend/js/team3/` (`dashboard.js`, `reports.js`, `notifications.js`, `backups.js`) to backend endpoints.
   * Connect login page to `/api/auth/login` and store JWT in browser `sessionStorage`/`localStorage`.

---

## ⚠️ Blocker & Resolution Log

| Issue ID | Description | Impact | Resolution / Status |
| :---: | :--- | :--- | :--- |
| **BLK-01** | Report generation during stock updates created inconsistent snapshots | Data discrepancy | Implemented `SystemStatus` check in `reports.py` returning `423 Locked` when `status != 'READY'`. |
| **BLK-02** | Inactive users remained logged in if token was not yet expired | Security risk | Added `verify_active_user()` query inside `@role_required` middleware to re-validate user state on every call. |
| **BLK-03** | Missing DDL and seed scripts for fresh setup | Developer friction | Documented complete schema DDL and single-line JSON restore utility in `docs/project-notes/database_setup_guide.md`. |
| **BLK-04** | Empty routes in `products.py` and `inventory.py` | Catalog incomplete | Prioritized for Sprint 4 backlog. |

