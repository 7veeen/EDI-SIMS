# SIMS Improvement 8 — Performance & Latency Optimization
## Phase 1: Read-Only Performance Audit Report

**Audit Date:** 2026-10-13  
**Auditor:** Senior Performance & Backend Engineer  
**System Under Audit:** Smart Inventory Management System (SIMS)  
**Status:** Read-Only Audit Completed (Zero Code or Schema Modifications)

---

## 1. Executive Summary & Architecture Overview

### 1.1 Architecture & Request-Flow Summary
SIMS is built with a decoupled architecture:
* **Frontend:** Vanilla HTML5, CSS3, and JavaScript Single Page Application (SPA).
* **Backend:** Python Flask REST API utilizing `flask_jwt_extended` for JWT authentication and custom role-based access control (RBAC).
* **Database:** Remote Supabase PostgreSQL database managed via raw SQL and `psycopg2-binary`.

```
[ Browser / Client ]
        │
        │ HTTP / REST (JSON)
        ▼
[ Flask Application (Routes / RBAC Middleware) ]
        │
        │ 1. verify_active_user() -> TCP/TLS + SELECT 1 query (psycopg2)
        │ 2. Service Handler -> New TCP/TLS + N sequential queries (psycopg2)
        ▼
[ Remote Supabase PostgreSQL (AWS/GCP Cloud Region) ]
```

### 1.2 Core Audit Takeaway
The application suffers from severe end-to-end latency across almost all endpoints:
* **Dashboard routes:** Median response times of **3.3s to 4.1s**.
* **Standard list and data routes:** Median response times of **2.0s to 3.0s**.
* **Authentication (`/api/auth/login`):** Median response time of **1.44s**.

**Crucial Finding:** The latency is **not** primarily driven by Python computation or in-engine query execution times (PostgreSQL execution time is <1 ms for individual queries on current dataset). Instead, latency is driven by two massive architectural multipliers:
1. **Zero Connection Pooling:** Every single database interaction opens a fresh TCP and SSL/TLS connection to remote Supabase, incurring **~834 ms** of connection overhead per connection. Furthermore, many HTTP requests open **multiple sequential connections** (one for RBAC `verify_active_user`, one for the service logic, and optionally one for audit logging).
2. **N-Query Sequential Round-Trip Waterfall:** Due to remote cloud hosting, network ping/round-trip latency is **~251 ms per query**. Endpoints like the Owner and Manager dashboards issue **13 to 14 sequential queries**, compounding wire round-trips into **3.5s+** of dead network waiting time.

---

## 2. Empirical Baseline Measurements (Workstream D)

All measurements were empirically captured on the active workspace using repeatable benchmark profilers (`benchmark_profiler.py`, `benchmark_comprehensive.py`, and `benchmark_dashboards.py`) running against the live Supabase PostgreSQL backend.

### 2.1 Database & Network Baseline Overheads
| Metric | Sample Count | Min | Median | P95 | Max | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **TCP/TLS Connection Handshake** | 5 | 761.1 ms | **834.0 ms** | 1044.3 ms | 1044.3 ms | `psycopg2.connect(DATABASE_URL)` to remote Supabase |
| **Wire Round-Trip (`SELECT 1`)** | 5 | 245.9 ms | **251.8 ms** | 295.8 ms | 295.8 ms | Single SQL query round-trip over active connection |
| **PostgreSQL In-Engine Planning & Execution** | N/A | 0.2 ms | **0.8 ms** | 2.1 ms | 2.2 ms | From `EXPLAIN (ANALYZE, BUFFERS)` |
| **Python Overhead (In-Memory Processing)** | N/A | 1.0 ms | **4.5 ms** | 12.0 ms | 15.0 ms | Serialization and dictionary mapping |

> **Measurement Insight:** The remote round-trip latency (251.8 ms) and connection handshake (834.0 ms) account for **>98%** of total request duration. Local Python execution and Postgres in-engine query processing account for **<2%**.

---

### 2.2 End-to-End API Baseline Latencies
Measurements taken over 5 repeatable sample iterations per endpoint using authenticated role sessions (`Owner`, `Manager`, `Employee`):

| Endpoint | Method | Role | Status | Response Size | Min Latency | Median Latency | P95 Latency | Max Latency | Sequential DB Conns |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | POST | Anonymous | 200 | 476 B | 1430.9 ms | **1440.2 ms** | 1578.8 ms | 1578.8 ms | 2 |
| `/api/dashboard/owner` | GET | Owner | 200 | 5,653 B | 3639.9 ms | **3823.3 ms** | 3943.8 ms | 3943.8 ms | 2 (14 queries) |
| `/api/dashboard/manager` | GET | Manager | 200 | 8,215 B | 4052.6 ms | **4091.0 ms** | 4224.8 ms | 4224.8 ms | 2 (13 queries) |
| `/api/dashboard/employee` | GET | Employee | 200 | 10,480 B | 3293.8 ms | **3370.0 ms** | 4018.9 ms | 4018.9 ms | 2 (6 queries) |
| `/api/inventory/` | GET | Owner | 200 | 4,035 B | 2008.9 ms | **2109.9 ms** | 2162.7 ms | 2162.7 ms | 2 (unpaginated) |
| `/api/products/?page=1&page_size=10` | GET | Owner | 200 | 2,437 B | 2161.3 ms | **2188.5 ms** | 2307.9 ms | 2307.9 ms | 2 (2 queries: count + rows) |
| `/api/purchase-orders/` | GET | Owner | 200 | 47,781 B | 2219.0 ms | **2435.3 ms** | 2472.8 ms | 2472.8 ms | 2 (unpaginated) |
| `/api/shipments/` | GET | Owner | 200 | 51,354 B | 2201.0 ms | **2374.8 ms** | 2457.7 ms | 2457.7 ms | 2 (unpaginated joins) |
| `/api/stock-requests/` | GET | Owner | 200 | 5,338 B | 2913.4 ms | **2982.5 ms** | 3303.5 ms | 3303.5 ms | 2 (complex subqueries) |
| `/api/invoices?page=1&limit=15` | GET | Owner | 200 | 794 B | 2041.2 ms | **2125.3 ms** | 2328.4 ms | 2328.4 ms | 2 (count + rows) |
| `/api/payments?page=1&limit=15` | GET | Owner | 200 | 524 B | 2068.1 ms | **2258.4 ms** | 2611.7 ms | 2611.7 ms | 2 (count + rows) |
| `/api/audit-logs/?page=1&limit=50` | GET | Owner | 200 | 9,701 B | 2159.5 ms | **2179.5 ms** | 2335.5 ms | 2335.5 ms | 2 (count + rows) |
| `/api/notifications/unread-count` | GET | Owner | 200 | 35 B | 2043.6 ms | **2046.8 ms** | 2257.4 ms | 2257.4 ms | 2 |
| `/api/notifications/` | GET | Owner | 200 | 31,836 B | 2153.3 ms | **2280.6 ms** | 2590.5 ms | 2590.5 ms | 2 (unpaginated) |

---

## 3. Ranked Bottlenecks & Empirical Evidence

### Rank 1 (Critical): Total Absence of Database Connection Pooling
* **Affected Files:**
  * `backend/app/extensions.py` (`get_db_connection`)
  * `backend/app/middleware/team1_auth.py` (`verify_active_user`)
  * All 18 route and service files across `team1`, `team2`, and `team3`.
* **Evidence:**
  * `backend/app/extensions.py` line 7-10 calls `psycopg2.connect(DATABASE_URL)` on every function invocation.
  * Measured connection establishment overhead: **834.0 ms median** (min 761.1 ms, max 1044.3 ms).
  * In `team1_auth.py` (`role_required` decorator), `verify_active_user()` opens and closes a connection to run `SELECT status FROM "Users" WHERE user_id = %s`.
  * Then, the wrapped service function immediately calls `get_db_connection()` to open a *second* connection.
  * In `POST /api/auth/login`, `login_user()` authenticates the user on connection 1, closes it, and then `log_audit_event()` opens connection 2 to record the login audit event.
* **Impact:** Every single authenticated API request spends **1.6s to 1.7s** purely establishing remote TLS connections before any application logic runs.

---

### Rank 2 (Critical): N-Query Sequential Waterfall in Dashboards
* **Affected Files:**
  * `backend/app/services/team3/dashboard_service.py` (`get_owner_dashboard`, `get_manager_dashboard`, `get_employee_dashboard`)
  * `backend/app/routes/team3/dashboard.py`
  * `frontend/js/pages/dashboard.js`
* **Evidence:**
  * `get_owner_dashboard()` executes **14 distinct sequential SQL queries** one after another on the same connection:
    1. Total products count
    2. Total inventory count
    3. Low stock count
    4. Out of stock count
    5. Inventory valuation
    6. Total purchase orders
    7. Pending purchase orders
    8. Active suppliers
    9. Pending stock requests
    10. Unread notifications
    11. Recent stock movements (limit 5)
    12. Low stock alert items (limit 5)
    13. Critical stock alerts count
    14. Warning stock alerts count
  * Network round-trip per query is **~251.8 ms**.
  * 14 sequential round-trips: $14 \times 251.8\text{ ms} = 3525.2\text{ ms}$.
  * With connection overhead (~800 ms), the median endpoint latency is **3823.3 ms**.
  * `get_manager_dashboard()` issues **13 sequential queries**, yielding **4091.0 ms** median latency.
  * `get_employee_dashboard()` issues **6 sequential queries**, yielding **3370.0 ms** median latency.
* **Impact:** The home/dashboard view—the first screen shown after login—takes ~4 seconds to render.

---

### Rank 3 (High): Unpaginated Endpoints & Large JSON Payloads
* **Affected Files:**
  * `backend/app/services/team1/inventory_service.py` (`get_inventory`)
  * `backend/app/services/team2/purchase_order_service.py` (`get_purchase_orders`)
  * `backend/app/services/team2/shipment_service.py` (`get_shipments`)
  * `backend/app/services/team2/stock_request_service.py` (`get_stock_requests`)
  * `backend/app/services/team3/notifications_service.py` (`get_all_notifications`)
  * `frontend/js/pages/inventory.js`, `purchase-orders.js`, `shipments.js`, `stock-requests.js`, `notifications.js`
* **Evidence:**
  * `GET /api/purchase-orders/` returns all rows with complete item lists (response size: **47.7 KB**).
  * `GET /api/shipments/` returns all rows with aggregated received and expected totals (response size: **51.4 KB**).
  * `GET /api/notifications/` returns all notifications for the user without limit (response size: **31.8 KB**).
  * Frontend scripts receive full payloads, loop through every element, and re-create all DOM table rows on every filter or search keypress via `innerHTML`.
* **Impact:** Payload sizes are already 30–50+ KB on minimal test records. As operational data grows into thousands of orders and shipments, payload transfer time and DOM parsing will severely degrade client responsiveness.

---

### Rank 4 (High): Subquery Aggregations & Missing Foreign Key / Filter Indexes
* **Affected Files:**
  * Database schema (`public."PurchaseOrders"`, `public."Shipments"`, `public."StockTransactions"`, `public."PurchaseOrderItems"`, `public."AuditLogs"`)
  * `backend/app/services/team2/shipment_service.py`
  * `backend/app/services/team2/stock_request_service.py`
* **Evidence:**
  * Inspection of `docs/project-notes/database_setup_guide.md` and database definitions reveals **zero secondary indexes** on:
    * `PurchaseOrders(status, supplier_id, order_date)`
    * `Shipments(status, purchase_order_id, supplier_id)`
    * `StockTransactions(shipment_id, transaction_type, product_id)`
    * `PurchaseOrderItems(purchase_order_id, product_id)`
    * `AuditLogs(action_time, user_id)`
    * `Notifications(user_id, is_read, created_at)`
  * `EXPLAIN (ANALYZE, BUFFERS)` execution plans reveal:
    * Shipments query performs full Sequential Scans on `StockTransactions` and `PurchaseOrderItems` inside subqueries, followed by `HashAggregate` and `Merge Left Join`.
    * Inventory query performs `Seq Scan` on `Inventory` and `Products`.
* **Impact:** While dataset sizes are currently small (<100 rows per table), sequential scans prevent PostgreSQL from scaling. With 10,000+ stock transactions or audit logs, query execution time will spike from <1 ms to hundreds of milliseconds.

---

### Rank 5 (Medium): Redundant Frontend API Requests & Render-Blocking Assets
* **Affected Files:**
  * `frontend/index.html`
  * `frontend/js/app.js`
  * `frontend/js/pages/notifications.js`
* **Evidence:**
  * **Duplicate Unread Count Fetch:** On application boot, `notifications.init()` invokes `updateUnreadCount()`. Immediately following, `App.navigate()` is called, which *also* invokes `notifications.updateUnreadCount()`. Both trigger `GET /api/notifications/unread-count` (~2046 ms each) concurrently on initial load.
  * **Route Change Waterfall:** Every internal navigation in `App.navigate(hash)` re-triggers `notifications.updateUnreadCount()`, adding an unnecessary 2-second background API call on every page switch.
  * **19 Synchronous `<script>` Tags:** `frontend/index.html` loads 19 JavaScript modules sequentially in the `<head>` without `defer` or `async`, blocking initial HTML parsing and layout until all 850+ KB of JavaScript are evaluated.
  * **External CSS CDN:** Render-blocking `<link>` to `unpkg.com/boxicons@2.1.4/css/boxicons.min.css` creates third-party DNS resolution, TLS handshake, and stylesheet blocking before first paint.

---

## 4. Root Cause Analysis

### 4.1 Connection Lifecycle Architecture Defect
* **Cause:** The backend was implemented using vanilla `psycopg2` utility functions (`get_db_connection()`) designed as simple helper scripts rather than an enterprise web service. No connection pool (such as `psycopg2.pool.ThreadedConnectionPool` or a persistent pool context) was initialized in Flask application factory.
* **Compounding Factor:** Separate middleware layers (`verify_active_user`) and logging hooks (`log_audit_event`) each manage their own database lifecycle independently rather than reusing a request-scoped connection from Flask `g`.

### 4.2 Architectural Query Splitting (Micro-Query Anti-Pattern)
* **Cause:** `dashboard_service.py` was constructed using clean, isolated helper functions (`_get_products_summary`, `_get_inventory_summary`, `_get_orders_summary`, etc.). Each helper issues 1 to 3 isolated queries.
* **Compounding Factor:** On a local database, 14 queries take 14 ms. On a remote cloud database with 250 ms wire latency, 14 queries take 3.5 seconds. The architecture did not account for geographic/network round-trip latency.

### 4.3 Omission of Pagination Contracts in Phase 1 Services
* **Cause:** When early services (Inventory, Purchase Orders, Shipments, Stock Requests) were created, simple `SELECT *` was implemented. Later services (Products, Invoices, Payments, Audit Logs) adopted `page` and `limit` query parameters, creating an inconsistent API contract.

---

## 5. Recommended Fixes, Impact, Risks, and Verification

| Bottleneck | Recommended Fix | Expected Latency Reduction | Risk Level | Verification Method |
| :--- | :--- | :---: | :---: | :--- |
| **Missing Connection Pooling** | Implement thread-safe connection pooling (`psycopg2.pool.ThreadedConnectionPool`) initialized in Flask `create_app()`. Manage connection checkout and checkin per request lifecycle using Flask `g.db_conn` and teardown handlers. | **~800 ms to 1600 ms** reduction across **all** endpoints | Low (purely infrastructural; preserves all SQL and RBAC logic) | Repeat baseline profiler; verify connection reuse count, pool exhaustion limits, and error handling. |
| **Dashboard Query Waterfall** | Consolidate 14 sequential queries into a single multi-metric SQL aggregation using CTEs (`WITH counts AS (...)`) or parallel JSON aggregation (`json_build_object`). | **~3,000 ms** reduction on Owner & Manager dashboards (from ~3.9s to **<0.5s**) | Medium (must match existing output dictionary schema exactly) | Validate JSON response compatibility with existing dashboard widgets and unit test suite. |
| **Redundant Auth DB Calls** | Cache active user status check or reuse `g.db_conn` so `verify_active_user` does not open a second connection. | **~800 ms** reduction on every authenticated endpoint | Low (RBAC checks remain strictly enforced) | Run full RBAC test suite (`tests/team1/test_auth.py`, `tests/team1/test_rbac.py`). |
| **Unpaginated Data Tables** | Add standard pagination (`page`, `limit`) to `Inventory`, `PurchaseOrders`, `Shipments`, and `StockRequests` services and frontend tables, matching `Products` and `Invoices`. | **30–50% payload reduction**, faster DOM render | Low | Test list filtering, pagination controls, and export routines. |
| **Missing DB Indexes** | Add focused composite B-tree indexes on foreign keys and high-frequency filter columns (`status`, `order_date`, `action_time`). | Prevents future linear query degradation as data grows | Low (no write-path lock risks on current table sizes) | Re-run `EXPLAIN (ANALYZE, BUFFERS)` to verify index scans replace sequential scans. |
| **Frontend Assets & Unread Polling** | Add `defer` to scripts in `index.html`. Debounce/deduplicate `notifications.updateUnreadCount()` so it only fires once on boot and periodically via polling/visibility change rather than every navigation. | **~2,000 ms** reduction in background traffic on navigation | Very Low | Observe Network tab in browser for zero duplicate requests. |

---

## 6. Prioritized Phase 2 Implementation Plan

Once approved, Phase 2 should proceed in the following prioritized sequence:

### Step 1: Backend Connection Pooling & Request-Scoped DB Management (Highest ROI)
1. Initialize `ThreadedConnectionPool` in `backend/app/extensions.py` using `DATABASE_URL`, `minconn=2`, `maxconn=10`.
2. Implement request-lifecycle connection acquisition via Flask `@app.before_request` and `@app.teardown_appcontext`.
3. Update `verify_active_user()` and service calls to reuse the request-scoped connection rather than opening standalone connections.
4. Verify baseline latency across all 14 endpoints. Expected global latency drop: ~800–1600 ms across the entire API.

### Step 2: Dashboard Query Consolidation (Highest User Impact)
1. Rewrite `get_owner_dashboard()` and `get_manager_dashboard()` in `backend/app/services/team3/dashboard_service.py` to fetch summary metrics in a single consolidated SQL query (e.g. using `SELECT ... FROM (SELECT count(*) ...), (SELECT count(*) ...)`).
2. Fetch recent lists (low stock alert items, recent stock movements) in 1 or 2 combined queries instead of 8 separate calls.
3. Validate exact key-value parity with current dashboard JSON schemas.
4. Expected dashboard latency drop: from ~3.9s to <0.6s.

### Step 3: Frontend Request Deduplication & Asset Optimization
1. Add `defer` to all module `<script>` tags in `frontend/index.html`.
2. In `frontend/js/app.js` and `frontend/js/pages/notifications.js`, remove duplicate initial unread-count trigger.
3. Throttle or gate `notifications.updateUnreadCount()` during rapid route changes.
4. Add skeleton/loading states in frontend dashboard views for perceived performance.

### Step 4: Endpoint Pagination Standardization
1. Update `backend/app/services/team1/inventory_service.py`, `backend/app/services/team2/purchase_order_service.py`, and `backend/app/services/team2/shipment_service.py` to accept optional `page` and `limit` query parameters with safe defaults (e.g., default 50 rows).
2. Wire frontend table pagination controls for Inventory and Purchase Orders.

### Step 5: Database Index Optimization Migration (Coordinated)
1. Prepare a safe SQL migration script containing:
   * `CREATE INDEX IF NOT EXISTS idx_po_status ON "PurchaseOrders" (status);`
   * `CREATE INDEX IF NOT EXISTS idx_shipments_po_id ON "Shipments" (purchase_order_id);`
   * `CREATE INDEX IF NOT EXISTS idx_stock_tx_shipment ON "StockTransactions" (shipment_id, transaction_type);`
   * `CREATE INDEX IF NOT EXISTS idx_audit_time ON "AuditLogs" (action_time DESC);`
   * `CREATE INDEX IF NOT EXISTS idx_notif_user_unread ON "Notifications" (user_id, is_read);`
2. Execute migration safely and verify `EXPLAIN` execution plans.

---

## 7. Compliance with Strict Constraints

* **Read-Only Audit:** Zero application source files, styles, or scripts were modified.
* **Database Schema Preservation:** Zero indexes were created, no tables or columns altered, zero RLS policies modified, and zero live data changed.
* **Security & Auth:** No JWT validations, RBAC rules, audit logs, or notifications were disabled or bypassed.
* **Working Tree:** All existing working tree modifications from prior phases were strictly preserved.

---
*End of Phase 1 Audit Report. Awaiting explicit user approval before proceeding to Phase 2 implementation.*
