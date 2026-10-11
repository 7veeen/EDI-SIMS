# SIMS — Backup and Restore Page Review, Testing & Verification Report

**Document ID:** `SIMS-BRR-2026-10-11`  
**Date:** October 11, 2026  
**Module:** Backup and Restore / Disaster Recovery  
**Auditor:** Antigravity Pair-Programming Agent (DeepMind)  
**Acceptance Status:** **PASS WITH LIMITATIONS**

---

## 1. Executive Summary

A comprehensive architectural inspection, security audit, artifact validation, and regression testing cycle was executed for the **Backup and Restore page** in the Smart Inventory Management System (SIMS).

The verification evaluated the operational flow:
$$\text{Backup UI } (\texttt{backups.js}) \longrightarrow \text{API Client } (\texttt{Api.post}) \longrightarrow \text{Flask Route } (\texttt{/api/backups/}) \longrightarrow \text{Export Engine } \longrightarrow \text{Artifact Storage } (\texttt{backend/backups/}) \ \& \ \texttt{"BackupHistory"}$$

### Key Findings & Verdict:
1. **Backup Creation & Storage Verified:** Authenticated Owner requests successfully trigger full logical JSON backups across all 19 public PostgreSQL tables. The generated artifact (`inventory_backup_20261011_155210.json`, 6.32 MB) was verified on disk, validated via JSON schema parser, and confirmed to maintain 100% relational foreign-key consistency.
2. **Strict Server-Side RBAC Confirmed:** `@role_required("Owner")` protects both `GET /api/backups/` and `POST /api/backups/`. Anonymous requests receive `401 Unauthorized`; Manager, Employee, and Supplier roles are strictly rejected with `403 Forbidden`.
3. **Confirmed Defects Remediated:** 
   - Remediated DOM-based XSS vulnerabilities in `frontend/js/pages/backups.js` by wrapping all table fields (`backup_name`, `backup_type`, `backup_size`, `status`, error messages) in `Utils.escapeHtml()`.
   - Enriched `GET /api/backups/` with a non-destructive `LEFT JOIN "Users"` to resolve creator usernames (`demo_owner`, `manager1`) rather than displaying raw user IDs.
4. **Restore Status — NOT VERIFIED on Live Database:** In strict compliance with safety rules, no destructive restore was executed against the shared Supabase PostgreSQL database. Because the application currently lacks an automated restore API endpoint (`POST /api/backups/restore`) and an isolated PostgreSQL instance was not available, the restore capability is documented as **NOT VERIFIED**.
5. **Final Status:** **PASS WITH LIMITATIONS** (Backup creation, history, RBAC, and artifact validation fully pass; automated restore remains an outstanding enhancement).

---

## 2. Existing Architecture and Files Inspected

| Component | File / Object | Role & Responsibilities |
| :--- | :--- | :--- |
| **Frontend UI** | [`frontend/js/pages/backups.js`](file:///d:/7even%20repica%202/frontend/js/pages/backups.js) | Renders `#backups-table`, provides `#btn-create-backup` action, manages loading spinners, toasts, and history display. |
| **Frontend Router** | [`frontend/js/app.js`](file:///d:/7even%20repica%202/frontend/js/app.js#L23) | Configures sidebar route `{ path: 'backups', icon: 'bx-data', label: 'Backup & Restore', roles: ['Owner'] }`. |
| **Backend Routes** | [`backend/app/routes/team3/backups.py`](file:///d:/7even%20repica%202/backend/app/routes/team3/backups.py) | Exposes `GET /api/backups/` (list) and `POST /api/backups/` (create) protected with `@role_required("Owner")`. |
| **Auth Middleware** | [`backend/app/middleware/team1_auth.py`](file:///d:/7even%20repica%202/backend/app/middleware/team1_auth.py) | Decodes JWT identity, enforces Owner-only authorization. |
| **Database Table** | `public."BackupHistory"` (Supabase PostgreSQL) | Persistent ledger tracking `backup_id`, `backup_name`, `backup_type`, `backup_date`, `backup_size`, `created_by`, `status`. |
| **Artifact Destination**| `backend/backups/` (Local Filesystem) | Destination folder storing serialized JSON snapshots (`inventory_backup_<timestamp>.json`). Ignored by Git via `.gitignore`. |
| **Setup & Seeding Guide**| [`docs/project-notes/database_setup_guide.md`](file:///d:/7even%20repica%202/docs/project-notes/database_setup_guide.md#L210) | Documents developer-side Python snippet for manual initial data restoration from JSON backups. |

---

## 3. Backup and Restore UI Verification

### 3.1 Backup Interface & History
- **Mount & Display:** Navigating to `#backups` renders the actions header and table without JavaScript console errors.
- **Action Control:** The **Create New Backup** button (`#btn-create-backup`) displays a confirmation prompt: `"Creating a full system backup may take some time. Do you want to proceed?"`.
- **Loading & Concurrency Defense:** Upon confirmation, the button is immediately disabled (`btn.disabled = true`) and displays a spinner (`<i class='bx bx-loader-alt bx-spin'></i> Backing up...`), preventing double-clicks and concurrent requests.
- **History Rendering:** Persisted records load into `#backups-table` with columns: `ID`, `Backup Name`, `Type`, `Size`, `Date`, `Status`, `Created By`.
- **Badge Styling:** Backups with status `Success` receive green pill badges (`status-active`); failed attempts receive inactive styling (`status-inactive`).
- **Creator Resolution:** The creator column cleanly renders the resolved username (`demo_owner`) or falls back to `User #<id>`.
- **Error Handling:** Network or server errors display a prominent warning row in the table body without leaving the page in a permanent loading state.

### 3.2 Restore Interface Status
- **Current State:** The existing UI does **not** feature restore buttons, modals, or file upload pickers.
- **Classification:** An automated restore interface is currently absent from the frontend, classified as an **Outstanding Enhancement**.

---

## 4. Backup Creation Mechanism

The backup creation routine in `backend/app/routes/team3/backups.py` executes the following sequence:

1. **Identity Resolution:** Extracts the caller's JWT identity via `get_jwt_identity()`. If `created_by` is supplied in the request body, validates that the user exists in `public."Users"`.
2. **Schema Discovery:** Queries PostgreSQL metadata:
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
   ORDER BY table_name;
   ```
3. **Table Data Extraction:** Dynamically queries every discovered public table (`SELECT * FROM <table_name>`) and serializes records via custom `json_serializer` (converting dates to ISO 8601 strings and `Decimal` to `float`).
4. **File Serialization:** Writes the aggregated dictionary into `backend/backups/inventory_backup_<timestamp>.json` with `indent=2, ensure_ascii=False`.
5. **Metadata Ledgering:** Computes the human-readable file size (e.g. `6.32 MB`) and records the entry in `public."BackupHistory"` with `status = 'Success'`.
6. **Response:** Returns HTTP `201 Created` with full metadata and the absolute file path.

---

## 5. Database and Schema Coverage

An exhaustive schema inspection compared the backup mechanism against all 19 public base tables in Supabase PostgreSQL:

| Table Name | Live Row Count | Captured in Backup Artifact | Field Data Serialized |
| :--- | :---: | :---: | :---: |
| `AuditLogs` | 205 | **YES** | `log_id`, `user_id`, `action`, `table_name`, `record_id`, `action_time`, `ip_address` |
| `BackupHistory` | 13 | **YES** | `backup_id`, `backup_name`, `backup_type`, `backup_date`, `backup_size`, `created_by`, `status` |
| `Categories` | 12 | **YES** | `category_id`, `category_name`, `description`, `created_at` |
| `Inventory` | 13 | **YES** | `inventory_id`, `product_id`, `quantity`, `location`, `last_updated` |
| `Notifications` | 626 | **YES** | `notification_id`, `user_id`, `type`, `title`, `message`, `is_read`, `created_at` |
| `OrderStatusHistory` | 360 | **YES** | `history_id`, `order_id`, `old_status`, `new_status`, `changed_by`, `changed_at`, `notes` |
| `Products` | 13 | **YES** | `product_id`, `name`, `sku`, `category_id`, `unit_price`, `stock_quantity`, `reorder_level` |
| `PurchaseOrderItems` | 93 | **YES** | `purchase_order_item_id`, `purchase_order_id`, `product_id`, `quantity`, `unit_price`, `subtotal` |
| `PurchaseOrders` | 95 | **YES** | `purchase_order_id`, `supplier_id`, `ordered_by`, `order_date`, `expected_delivery`, `total_amount`, `status` |
| `Reports` | 328 | **YES** | `report_id`, `report_type`, `report_name`, `report_data` (JSONB), `generated_by`, `created_at` |
| `Roles` | 4 | **YES** | `role_id`, `role_name`, `description` |
| `Shipments` | 53 | **YES** | `shipment_id`, `purchase_order_id`, `tracking_number`, `carrier`, `status`, `shipped_date`, `delivery_date` |
| `StockRequestItems` | 10 | **YES** | `item_id`, `request_id`, `product_id`, `quantity` |
| `StockRequests` | 7 | **YES** | `request_id`, `requested_by`, `request_date`, `status`, `urgency` |
| `StockTransactions` | 69 | **YES** | `transaction_id`, `product_id`, `transaction_type`, `quantity`, `unit_price`, `transaction_date`, `performed_by` |
| `SupplierQuotations` | 55 | **YES** | `quotation_id`, `request_id`, `supplier_id`, `unit_price`, `total_price`, `valid_until`, `status` |
| `Suppliers` | 2 | **YES** | `supplier_id`, `company_name`, `contact_name`, `email`, `phone`, `status` |
| `SystemStatus` | 1 | **YES** | `module_name`, `status`, `progress`, `message`, `updated_at` |
| `Users` | 20 | **YES** | `user_id`, `username`, `email`, `password_hash`, `role_id`, `status`, `created_at` |

### Scope Coverage Analysis: What is Included vs Omitted

| Architectural Element | Included in Backup? | Explanation & Impact |
| :--- | :---: | :--- |
| **Table Row Data** | **YES (100%)** | All 19 public tables and their row data are serialized into structured JSON. |
| **JSONB Objects** | **YES** | Complex JSONB columns (such as `Reports.report_data`) are preserved. |
| **DDL Table Schemas** | **NO** | No `CREATE TABLE` DDL statements are generated. Restoration requires pre-existing table schemas. |
| **Foreign Key Constraints** | **NO** | Foreign key values are preserved as raw integer columns, but foreign key constraint DDL is not included. |
| **Indexes & Keys** | **NO** | B-tree indexes, primary key constraints, and unique constraints are omitted from the artifact. |
| **PostgreSQL Sequences** | **NO** | Sequence offsets (`pg_sequences`) are not exported. Restoring data without `setval()` may cause PK collisions. |
| **Stored Triggers & Functions** | **NO** | PL/pgSQL routines (such as `create_audit_log()`) are not captured. |

---

## 6. Backup Artifact Integrity

A newly generated backup artifact was subjected to filesystem and relational integrity checks:

- **Artifact Name:** `inventory_backup_20261011_155210.json`
- **Filesystem Location:** `D:\7even repica 2\backend\backups\inventory_backup_20261011_155210.json`
- **File Size:** `6,626,878 bytes` (~6.32 MB)
- **JSON Validity:** Parsed completely with `json.load()` without parse errors.
- **Relational Consistency:**
  - `Products` $\rightarrow$ `Categories`: 100% of product `category_id` values match existing categories.
  - `Users` $\rightarrow$ `Roles`: 100% of user `role_id` values match existing roles.
  - `Inventory` $\rightarrow$ `Products`: 100% of inventory `product_id` references match existing products.
  - `PurchaseOrderItems` $\rightarrow$ `PurchaseOrders` & `Products`: 100% of foreign keys resolve.
  - `Shipments` $\rightarrow$ `PurchaseOrders`: 100% of shipment `purchase_order_id` values resolve.

---

## 7. Restore Workflow and Recovery Verification

### 7.1 Existing Restore Workflow
Currently, database restoration is documented in [`docs/project-notes/database_setup_guide.md`](file:///d:/7even%20repica%202/docs/project-notes/database_setup_guide.md#L210) as a manual developer script. There is no automated API route (`POST /api/backups/restore`) or web UI trigger.

### 7.2 Safety Determination & Verification Status
Per the prompt's mandatory safety rules:
> *"Do not perform a restore against the shared or production Supabase database during this review. Do not drop tables, truncate data, delete records, or overwrite existing backups."*
> *"If an isolated restore environment is unavailable, test backup validation safely and report restore verification as **NOT VERIFIED**, rather than claiming success."*

**Status:** **NOT VERIFIED (ON LIVE DATABASE)**  
- Live database restore was intentionally bypassed to safeguard persistent production records.
- Logical schema and relational dependency verification of the backup JSON file **PASSED**.

---

## 8. Authentication and RBAC

Security testing was executed against `/api/backups/`:

| Identity Tested | Token Header | Method | Expected Status | Actual Status | RBAC Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Anonymous** | None | `GET` | `401 Unauthorized` | `401 Unauthorized` | **PASSED** |
| **Anonymous** | None | `POST` | `401 Unauthorized` | `401 Unauthorized` | **PASSED** |
| **Supplier (`demo_supplier`)** | Valid Supplier JWT | `GET` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Supplier (`demo_supplier`)** | Valid Supplier JWT | `POST` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Employee (`demo_employee`)** | Valid Employee JWT | `GET` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Employee (`demo_employee`)** | Valid Employee JWT | `POST` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Manager (`demo_manager`)** | Valid Manager JWT | `GET` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Manager (`demo_manager`)** | Valid Manager JWT | `POST` | `403 Forbidden` | `403 Forbidden` | **PASSED** |
| **Owner (`demo_owner`)** | Valid Owner JWT | `GET` | `200 OK` | `200 OK` | **PASSED** |
| **Owner (`demo_owner`)** | Valid Owner JWT | `POST` | `201 Created` | `201 Created` | **PASSED** |

---

## 9. Storage Security and Retention

1. **Storage Location:** Backups are written to `backend/backups/` outside the web root (`frontend/`). They are not directly accessible via public HTTP URLs.
2. **Path Traversal Protection:** The backup filename is programmatically generated on the server (`inventory_backup_<timestamp>.json`). User input cannot specify arbitrary output paths.
3. **Git Hygiene:** `backups/` is listed in `.gitignore`, preventing accidental commits of database snapshots containing password hashes or personal data.
4. **Retention Policy:** Currently, backups are retained indefinitely on the application server's local disk without automatic rotation. Disk monitoring is recommended for enterprise scale.

---

## 10. Failure-Scenario Test Results

| # | Scenario Tested | Simulation / Action | Expected Behavior | Actual Behavior | Result |
| :-: | :--- | :--- | :--- | :--- | :---: |
| 1 | **Anonymous Access** | Unauthenticated request | Rejected with HTTP 401 | HTTP 401 returned | **PASSED** |
| 2 | **Unauthorized Role** | Manager JWT | Rejected with HTTP 403 | HTTP 403 returned | **PASSED** |
| 3 | **Invalid Creator User ID** | `created_by: 999999` | Rejected with HTTP 400 | HTTP 400 (`Invalid user_id`) | **PASSED** |
| 4 | **Database Connection Failure** | Mocked DB failure | Returns HTTP 500 without crashing | Returns HTTP 500 cleanly | **PASSED** |
| 5 | **DOM XSS Injection** | Injected `<script>` in backup name | Rendered text escaped in table | Escaped via `Utils.escapeHtml` | **PASSED** |
| 6 | **Missing Creator Display** | Unjoined or deleted user ID | Fallback to `User #<id>` | Displays clean fallback | **PASSED** |
| 7 | **Concurrent Click Prevention** | User clicks button rapidly | Button disabled during request | Disabled with spinner | **PASSED** |

---

## 11. Auditability and Operational Safety

- **Operational History:** Every successful backup operation creates an audit entry in `public."BackupHistory"` containing the artifact name, size, type, timestamp, and creator ID.
- **Centralized AuditLogs Status:** The centralized `AuditLogs` table currently does **not** receive a separate `BACKUP_CREATED` event. This is consistent with the Phase 8 audit scope (which focused on transactional inventory and procurement events) and is classified as an **Optional Enhancement**.

---

## 12. Automated Test Results

### 12.1 Execution Summary

| Test Suite / Script | Target Scope | Tests Run | Passed | Failed |
| :--- | :--- | :---: | :---: | :---: |
| [`tests/team3/test_backups.py`](file:///d:/7even%20repica%202/tests/team3/test_backups.py) | Full automated backup & RBAC test suite | 6 | 6 | 0 |
| [`scratch/test_backup_creation_and_validation.py`](file:///d:/7even%20repica%202/scratch/test_backup_creation_and_validation.py) | Live backup creation, artifact inspection, RBAC | 4 | 4 | 0 |
| [`scratch/test_backup_relational_integrity.py`](file:///d:/7even%20repica%202/scratch/test_backup_relational_integrity.py) | Relational foreign-key consistency check | 6 | 6 | 0 |
| [`scratch/test_frontend_backups.js`](file:///d:/7even%20repica%202/scratch/test_frontend_backups.js) | Frontend DOM rendering & XSS security harness | 2 | 2 | 0 |
| [`tests/team3/test_status.py`](file:///d:/7even%20repica%202/tests/team3/test_status.py) | Regression check on System Health module | 10 | 10 | 0 |
| **Total Automated Tests** | — | **28** | **28** | **0** |

### 12.2 Pytest Command Output
```text
pytest tests/team3/test_status.py tests/team3/test_backups.py -q
................                                                         [100%]
16 passed in 49.62s
```

---

## 13. Files Modified and Reasons

| File | Modification Type | Description & Rationale |
| :--- | :---: | :--- |
| [`frontend/js/pages/backups.js`](file:///d:/7even%20repica%202/frontend/js/pages/backups.js#L54-L74) | Security Fix | Added `Utils.escapeHtml()` to all table columns (`backup_name`, `backup_type`, `backup_size`, `status`, error messages) to eliminate DOM XSS risks, and resolved creator usernames gracefully. |
| [`backend/app/routes/team3/backups.py`](file:///d:/7even%20repica%202/backend/app/routes/team3/backups.py#L38-L67) | Usability Enhancement | Added `LEFT JOIN "Users" u ON bh.created_by = u.user_id` to provide `creator_username` in `GET /api/backups/` responses while preserving all existing keys. |
| [`tests/team3/test_backups.py`](file:///d:/7even%20repica%202/tests/team3/test_backups.py) | Test Suite | Created comprehensive automated pytest test suite covering RBAC, artifact validation, error handling, and history retrieval. |

---

## 14. Database and Storage Safety

- **No Destructive Database Changes:** No tables were dropped, truncated, or modified.
- **Historical Data Preserved:** Existing records in `BackupHistory` (12 historical + 1 test-created = 13 total) and `AuditLogs` remain intact.
- **Isolated Artifact Generation:** The backup artifact was written to local storage without affecting live database operations.

---

## 15. Confirmed Defects Fixed

### Defect 1: DOM XSS Vulnerability in Backup Table
- **Severity:** High (Security)
- **Description:** `frontend/js/pages/backups.js` interpolated `b.backup_type`, `b.backup_size`, and `b.status` directly into `innerHTML` without sanitization. If malicious input was stored in `BackupHistory`, arbitrary script execution could occur.
- **Resolution:** Wrapped all rendered row strings in `Utils.escapeHtml()`.
- **Status:** **FIXED**

### Defect 2: Unresolved Creator Usernames
- **Severity:** Low (Usability)
- **Description:** Backups table displayed raw `User #<id>` without resolving human-readable usernames.
- **Resolution:** Enriched `GET /api/backups/` with `creator_username` via `LEFT JOIN "Users"`.
- **Status:** **FIXED**

---

## 16. Outstanding Defects and Optional Enhancements

### Outstanding Enhancements
1. **Automated Web Restore Endpoint (`POST /api/backups/<id>/restore`):** Implementing a transactional restore endpoint that parses the JSON backup, disables foreign-key checks temporarily, restores records in dependency order, and updates sequence counters with `setval()`.
2. **Centralized Audit Trail Integration:** Emitting `BACKUP_CREATED` events to `AuditLogs` upon successful backup generation.
3. **Backup Retention & Rotation Policy:** Implementing automatic cleanup of backup files older than 30 days to manage disk utilization.
4. **Physical DDL Dumps (`pg_dump`):** Providing option for full PostgreSQL DDL dumps alongside logical JSON data snapshots.

---

## 17. Limitations and Tests Not Run

1. **Live Database Restoration:** Intentionally **not executed** on the shared Supabase PostgreSQL instance to protect historical business and audit records from data loss or corruption.
2. **Dedicated Disposable PostgreSQL Instance:** An isolated, disposable PostgreSQL database was not available in this environment to execute a live physical restoration test.

---

## 18. Final Acceptance Status

### Status: **PASS WITH LIMITATIONS**

**Justification:**
Backup creation, metadata persistence, RBAC access control, artifact integrity, relational dependency consistency, and frontend security fully passed all verification tests. However, because restoration was **NOT VERIFIED** against a live or disposable database and automated web restore is not yet implemented, the status is formally designated as **PASS WITH LIMITATIONS**.
