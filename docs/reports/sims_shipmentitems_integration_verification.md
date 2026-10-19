# SIMS — ShipmentItems Migration, Backend/API, and UI Integration Verification Report

**Target System:** Smart Inventory Management System (SIMS)  
**Database:** Supabase PostgreSQL (`db.hltosdkwugwcpofekjgp.supabase.co:5432`)  
**Audit Date:** October 19, 2026  
**Auditor:** Antigravity AI  
**Scope:** Verification of `ShipmentItems` Table Existence, Migration Status, Backend Services, API Routes, Frontend UI, and Automated Test Coverage  
**Audit Classification:** READ-ONLY Verification (Zero database mutations, zero application code alterations)  

---

## 1. Executive Summary

This independent audit verified whether the `ShipmentItems` table exists in the live Supabase PostgreSQL database, whether its migration was formally applied and tracked, and whether the backend services, API endpoints, and frontend user interface are correctly integrated with the table.

### Audit Outcome: **TABLE EXISTS BUT INTEGRATION IS INCOMPLETE**

### Key Findings Summary:
1. **Live Database Table Exists:** The table `public."ShipmentItems"` physically exists in the live Supabase PostgreSQL database. Its column types, primary key, foreign keys (`ON DELETE CASCADE` to `Shipments`, `RESTRICT` to `Products`), positive-quantity check constraint (`quantity > 0`), uniqueness constraint (`UNIQUE (shipment_id, product_id)`), and B-Tree indexes match the architectural specification.
2. **Migration Not Formally Tracked / File Untracked in Git:** The migration script [`database/migrations/003_create_shipment_items.sql`](file:///d:/7even%20repica%202/database/migrations/003_create_shipment_items.sql) exists in the local workspace filesystem and its DDL matches the live table definition. However:
   - The file is **untracked in git** (has not been committed to version control).
   - The live PostgreSQL instance has **no schema migration tracking table** for the `public` schema; the DDL was applied directly to the database during Phase C development without recorded migration metadata.
3. **Zero Allocation Data in Live Database:** The live table contains **0 rows**. All **65 existing shipments** in `public."Shipments"` have zero line-item allocation rows in `ShipmentItems` (100% legacy unallocated records).
4. **Backend Services & API Layer Fully Integrated:** The backend service layer ([`shipment_service.py`](file:///d:/7even%20repica%202/backend/app/services/team2/shipment_service.py) and [`inventory_service.py`](file:///d:/7even%20repica%202/backend/app/services/team1/inventory_service.py)) and API endpoints (`POST /api/shipments/`, `GET /api/shipments/<id>`, and `POST /api/inventory/stock-in`) properly accept, validate, insert, query, and enforce line-level shipment allocations with parent PO row-locking (`FOR UPDATE`) and safe legacy fallbacks.
5. **Critical Frontend Integration Gap:** The **Create Shipment modal** in [`frontend/js/pages/shipments.js`](file:///d:/7even%20repica%202/frontend/js/pages/shipments.js) (lines 490–646) **completely omits item allocation inputs and does not transmit the `items` array in its POST payload**. As a direct consequence, all shipments generated through the user interface are created without allocation rows, explaining why `ShipmentItems` remains empty in production.
6. **Shipment Details & Stock-In UI Ready for Allocations:** The Shipment Details modal and Receive Stock modal in [`frontend/js/pages/shipments.js`](file:///d:/7even%20repica%202/frontend/js/pages/shipments.js) are already coded to display and enforce allocated items and quantities when present.
7. **Test Evidence Scope:** 34 focused unit tests (Phase A, Phase B, Phase C) pass with 100% success. However, all 34 tests execute against **in-memory mocks**; zero automated integration tests against live Supabase PostgreSQL or live multi-connection concurrency tests currently exist in the test suite for `ShipmentItems`.

---

## 2. Live Table Existence and Schema Verification

Direct, read-only queries against PostgreSQL system catalogs (`information_schema.tables`, `information_schema.columns`, `pg_constraint`, and `pg_index`) on the live Supabase instance confirm the following live state:

### 2.1 Table Existence
- **Schema:** `public`
- **Table Name:** `"ShipmentItems"`
- **Existence:** **CONFIRMED** (Table exists in active Supabase PostgreSQL catalog)

### 2.2 Live Column Definitions
| Column Name | Data Type | Nullable | Default | Specification Match |
|---|---|---|---|---|
| `shipment_item_id` | `bigint` | `NO` | `nextval('"ShipmentItems_shipment_item_id_seq"'::regclass)` | **MATCH** (`BIGSERIAL PRIMARY KEY`) |
| `shipment_id` | `bigint` | `NO` | *None* | **MATCH** (`BIGINT NOT NULL`) |
| `product_id` | `bigint` | `NO` | *None* | **MATCH** (`BIGINT NOT NULL`) |
| `quantity` | `integer` | `NO` | *None* | **MATCH** (`INTEGER NOT NULL`) |
| `created_at` | `timestamp with time zone` | `YES` | `now()` | **MATCH** (`TIMESTAMPTZ DEFAULT NOW()`) |

### 2.3 Live Constraints
| Constraint Name | Type | Live Definition | Specification Match |
|---|---|---|---|
| `ShipmentItems_pkey` | Primary Key (`p`) | `PRIMARY KEY (shipment_item_id)` | **MATCH** |
| `ShipmentItems_shipment_id_fkey` | Foreign Key (`f`) | `FOREIGN KEY (shipment_id) REFERENCES "Shipments"(shipment_id) ON DELETE CASCADE` | **MATCH** |
| `ShipmentItems_product_id_fkey` | Foreign Key (`f`) | `FOREIGN KEY (product_id) REFERENCES "Products"(product_id)` | **MATCH** |
| `ShipmentItems_quantity_check` | Check (`c`) | `CHECK ((quantity > 0))` | **MATCH** |
| `uq_shipment_product` | Unique (`u`) | `UNIQUE (shipment_id, product_id)` | **MATCH** |

### 2.4 Live Indexes
| Index Name | Index Type | Live Definition | Specification Match |
|---|---|---|---|
| `ShipmentItems_pkey` | B-Tree (Unique) | `CREATE UNIQUE INDEX "ShipmentItems_pkey" ON public."ShipmentItems" USING btree (shipment_item_id)` | **MATCH** |
| `uq_shipment_product` | B-Tree (Unique) | `CREATE UNIQUE INDEX uq_shipment_product ON public."ShipmentItems" USING btree (shipment_id, product_id)` | **MATCH** |
| `idx_shipment_items_shipment_id` | B-Tree (Secondary) | `CREATE INDEX idx_shipment_items_shipment_id ON public."ShipmentItems" USING btree (shipment_id)` | **MATCH** |
| `idx_shipment_items_product_id` | B-Tree (Secondary) | `CREATE INDEX idx_shipment_items_product_id ON public."ShipmentItems" USING btree (product_id)` | **MATCH** |

---

## 3. Migration Application Status and Supporting Evidence

### 3.1 Migration File Verification
- **File Location:** [`database/migrations/003_create_shipment_items.sql`](file:///d:/7even%20repica%202/database/migrations/003_create_shipment_items.sql)
- **Status in Workspace:** Exists on disk.
- **SQL Parity:** The DDL contained within `003_create_shipment_items.sql` is a **100% character and structural match** to the live table, constraints, and index definitions cataloged above in Section 2.
- **Git Tracking Status:** `git status` reports the file as **untracked** (`Untracked files: database/migrations/003_create_shipment_items.sql`). It has not been committed to the repository history.

### 3.2 Migration History in Live Database
- **Schema Migration Tables:** An exhaustive catalog query (`SELECT schemaname, tablename FROM pg_tables WHERE tablename LIKE '%migration%' OR tablename LIKE '%schema%'`) found:
  - `auth.schema_migrations` (Supabase internal authentication migrations)
  - `storage.migrations` (Supabase internal storage migrations)
  - `realtime.schema_migrations` (Supabase internal realtime migrations)
  - **Zero** migration tracking tables exist in the `public` schema.
- **Project Migration Convention:** SIMS does not use an automated migration framework (e.g., Alembic, Flyway, Prisma, or Supabase CLI migration tracker). Previous migrations (`001_create_supplier_payments_and_invoices.sql` and `002_secure_supplier_payments_and_invoices_rls.sql`) were executed manually via transaction blocks.
- **Conclusion on Application Evidence:**
  The table was created directly on the Supabase database during Phase C implementation. Migration file `003_create_shipment_items.sql` was created after the fact to document the DDL, but neither an automated database migration log nor a committed git revision records its deployment.

---

## 4. Existing Allocation-Data Status

Live database queries executed on October 19, 2026 revealed:

| Metric | Query / Source | Count | Percentage |
|---|---|---|---|
| **Total Rows in `ShipmentItems`** | `SELECT COUNT(*) FROM public."ShipmentItems"` | **0** | — |
| **Total Rows in `Shipments`** | `SELECT COUNT(*) FROM public."Shipments"` | **65** | 100.0% |
| **Shipments With `ShipmentItems` Allocations** | `SELECT COUNT(DISTINCT shipment_id) FROM public."ShipmentItems"` | **0** | **0.0%** |
| **Shipments Without Allocation Records** | `Shipments Total - Shipments With Allocations` | **65** | **100.0%** |
| **Orphan Shipment Foreign Keys** | `ShipmentItems LEFT JOIN Shipments ... WHERE Shipments.id IS NULL` | **0** | 0.0% |
| **Orphan Product Foreign Keys** | `ShipmentItems LEFT JOIN Products ... WHERE Products.id IS NULL` | **0** | 0.0% |

### Analysis:
Every shipment currently recorded in SIMS is a **legacy shipment created without line-level allocations**. Because the Create Shipment frontend never transmits allocation lines, new shipments continue to be recorded with zero `ShipmentItems` entries.

---

## 5. Backend Service Findings

Backend service implementations were inspected across [`backend/app/services/team1/inventory_service.py`](file:///d:/7even%20repica%202/backend/app/services/team1/inventory_service.py) and [`backend/app/services/team2/shipment_service.py`](file:///d:/7even%20repica%202/backend/app/services/team2/shipment_service.py).

### 5.1 Shipment Creation & Allocation Validation
- **File & Function:** [`backend/app/services/team2/shipment_service.py`](file:///d:/7even%20repica%202/backend/app/services/team2/shipment_service.py), `create_shipment()` (lines 805–1098).
- **Finding 1 — Allocation Input Support:** Accepts `items` in payload (lines 880–886). Validates that `items` is a non-empty list of dictionaries with integer `product_id` and `quantity > 0`.
- **Finding 2 — PO Association Validation:** Validates that each allocated `product_id` belongs to the parent Purchase Order via `SELECT quantity FROM "PurchaseOrderItems" WHERE purchase_order_id = %s AND product_id = %s` (lines 908–917).
- **Finding 3 — PO Quantity Cap & Over-Allocation Prevention:** Checks previously allocated quantities across non-cancelled shipments via `SELECT COALESCE(SUM(si.quantity), 0) FROM "ShipmentItems" si JOIN "Shipments" s ON si.shipment_id = s.shipment_id WHERE s.purchase_order_id = %s AND si.product_id = %s AND s.status != 'Cancelled'` (lines 928–935). Rejects with error if `prev_alloc + qty > max_po_qty` (line 937).
- **Finding 4 — Concurrency Serialization on Creation:** Parent PO row is locked with `FOR UPDATE` (`SELECT ... FROM "PurchaseOrders" WHERE purchase_order_id = %s FOR UPDATE`, lines 837–842) before reading previous allocations or validating quantities. This guarantees that concurrent split-shipment dispatches cannot race to over-allocate the parent PO.
- **Finding 5 — Transactional Insertion:** Inserts into `"Shipments"` followed by iterative inserts into `"ShipmentItems"` within the same transaction (lines 957–1001). Commits at line 1069; executes `conn.rollback()` on any failure (line 1091).

### 5.2 Stock-In Goods Receipt & Allocation Enforcement
- **File & Function:** [`backend/app/services/team1/inventory_service.py`](file:///d:/7even%20repica%202/backend/app/services/team1/inventory_service.py), `stock_in()` (lines 390–810).
- **Finding 6 — Shipment-Level Allocation Path:** Looks up `SELECT quantity FROM "ShipmentItems" WHERE shipment_id = %s AND product_id = %s` (lines 459–464). When found:
  - Sets `expected_qty` strictly to the shipment's allocated quantity.
  - Computes `already_received` strictly for that `shipment_id` and `product_id` from `"StockTransactions"`.
  - Calculates `remaining_receivable = max(0, expected_qty - already_received)`.
  - Rejects if already fully received or if `quantity > remaining_receivable` (lines 479–485).
- **Finding 7 — Unallocated Product Rejection on Split Shipments:** If `ShipmentItems` records exist for the shipment, but the specific `product_id` is not present, it is rejected: `Product '{prod_name}' is not allocated to this shipment` (lines 487–496).
- **Finding 8 — Safe Legacy Fallback for Shipments Without Allocations:**
  - If no `ShipmentItems` records exist for the shipment:
    - **Single-Shipment Legacy POs (Case A):** Falls back to `PurchaseOrderItems` quantity, but calculates receipts across the entire PO to enforce a strict PO-wide receipt cap (lines 536–582).
    - **Ambiguous Multi-Shipment Legacy POs (Case B):** If more than one active non-cancelled shipment exists for the PO and neither has line-item allocations, stock-in is safely rejected with: `"Ambiguous legacy multi-shipment Purchase Order. This PO has multiple shipments without line-item allocations. Please reconcile shipment allocations before receiving stock."` (lines 530–534).
- **Finding 9 — Receiving Status Calculation:**
  - Evaluates all items in `ShipmentItems` for that shipment (lines 640–668).
  - Compares received quantity per item against allocated quantity.
  - Sets `Shipments.receiving_status` to `"Fully Received"` if all items reach allocated quantity, `"Partially Received"` if some quantity was received, or `"Pending Receipt"` (lines 709–721).
- **Finding 10 — Lock Ordering & Transaction Boundaries:**
  - Locks `Shipments` row first via `FOR UPDATE` (line 418).
  - Serializes legacy PO fallbacks via `PurchaseOrders` `FOR UPDATE` (line 509).
  - Locks `Inventory` row via `FOR UPDATE` (line 588).
  - Consistent lock order: `Shipments` -> (`PurchaseOrders`) -> `Inventory`. Prevents deadlocks.
  - Atomic commit at line 762; rolls back on any exception.

### 5.3 Shipment Detail Retrieval
- **File & Function:** [`backend/app/services/team2/shipment_service.py`](file:///d:/7even%20repica%202/backend/app/services/team2/shipment_service.py), `get_shipment_by_id()` (lines 350–542).
- **Finding 11 — Allocated Product Returns:** Queries `ShipmentItems` joined with `Products` and `PurchaseOrderItems` (lines 379–387). If found, returns the allocated items with `quantity`, `expected_quantity`, `received_quantity`, `remaining_quantity`, and `receiving_status`. If not found, falls back to `PurchaseOrderItems` for legacy records.

---

## 6. API Findings

API route handlers in [`backend/app/routes/team2/shipments.py`](file:///d:/7even%20repica%202/backend/app/routes/team2/shipments.py) and [`backend/app/routes/team1/inventory.py`](file:///d:/7even%20repica%202/backend/app/routes/team1/inventory.py) were verified:

| Route | Method | Roles Permitted | Implementation Function | Verification Finding |
|---|---|---|---|---|
| `/api/shipments/` | `POST` | `Supplier`, `Owner`, `Manager` | `add_shipment()` -> `create_shipment()` | Passes request JSON body directly to service. Returns `201 Created` with created shipment and allocated `items` array upon success. Returns `400 Bad Request` for allocation validation errors, `403 Forbidden` for ownership mismatches. |
| `/api/shipments/<id>` | `GET` | `Owner`, `Manager`, `Supplier`, `Employee` | `view_shipment()` -> `get_shipment_by_id()` | Returns `200 OK` with full shipment structure including `purchase_order.items` (containing allocated products, quantities, receiving statuses, and summary metrics `total_expected_quantity`, `total_received_quantity`, `total_remaining_quantity`). |
| `/api/inventory/stock-in` | `POST` | `Owner`, `Manager`, `Employee` | `perform_stock_in()` -> `stock_in()` | Enforces employee assignment. Returns `200 OK` on valid receipt. Returns `400 Bad Request` for over-receiving or ambiguous legacy shipments. |
| `/api/shipments/<id>/status` | `PATCH` | `Supplier`, `Owner`, `Manager` | `patch_shipment_status()` -> `update_shipment_status()` | Enforces state-machine transitions and returns `409 Conflict` on concurrent status races. |

**RBAC Preservation:** All role annotations (`@role_required`) and database-level tenancy / assignment filters are preserved.

---

## 7. Frontend/UI Findings

Frontend code in [`frontend/js/pages/shipments.js`](file:///d:/7even%20repica%202/frontend/js/pages/shipments.js) was analyzed against the backend API expectations:

### 7.1 Create Shipment Modal (`openCreateShipmentModal()`, lines 490–650)
- **Status:** **DEFECT / INCOMPLETE INTEGRATION**
- **Detailed Findings:**
  1. The modal contains fields for logistics carrier, tracking number, shipping method, dispatch status, package count, weight, origin address, destination address, expected delivery date, and shipping remarks.
  2. Selecting a Purchase Order triggers a listener (lines 618–645) that fetches `/purchase-orders/${poId}` and renders a **static, read-only summary** of the PO items (`previewBox.innerHTML`).
  3. **No input fields exist** for users to select which products to ship or specify line-item shipment quantities.
  4. The form submit handler (lines 574–612) builds a payload that **omits the `items` property entirely**:
     ```javascript
     await Api.post('/shipments/', {
         purchase_order_id: parseInt(poId),
         carrier: carrier || 'Standard Logistics',
         tracking_number: trackingNumber || null,
         shipping_method: method,
         status: status,
         package_count: pkgCount,
         total_weight: weightVal ? parseFloat(weightVal) : null,
         origin_address: origin,
         destination_address: dest,
         expected_delivery: expectedDelivery || null,
         shipping_notes: notes || ''
         // MISSING: items: [...]
     });
     ```
  5. Because `items` is never sent, the backend's `create_shipment()` function observes `data.get("items") is None` and skips inserting any rows into `ShipmentItems`.
  6. **Direct Impact:** The frontend cannot create shipments with line-level allocations. Every shipment dispatched via the web application is created as an unallocated legacy shipment.

### 7.2 Shipment Details Modal (`openShipmentDetailsModal()`, lines 808–968)
- **Status:** **PASS**
- **Detailed Findings:**
  - Reads `s.purchase_order.items`.
  - Correctly renders the "Shipment Contents & Receiving Progress" table displaying Product, SKU, Expected Quantity, Received Quantity, Remaining Quantity, and item Receiving Status badge.
  - Correctly reflects `s.receiving_status` and summary metric badges.

### 7.3 Goods Receipt / Stock-In Modal (`openReceiveStockModal()`, lines 1071–1231)
- **Status:** **PASS**
- **Detailed Findings:**
  - Filters receivable items from `s.purchase_order.items` where `remaining_quantity > 0`.
  - Sets the maximum selectable quantity on `<input type="number" id="stockin-quantity-input">` dynamically to the selected item's remaining quantity.
  - Validates client-side before sending POST request to `/api/inventory/stock-in`.
  - Supports partial receipts.

---

## 8. Focused Test Results and Limitations

### 8.1 Automated Test Execution Results
The focused test suites covering Phase A, Phase B, and Phase C remediations were executed:

```
Ran 34 tests in 112.696s
OK
```

#### Breakdown by Test Class:
1. **`ShipmentConcurrencyPhaseATestCase` ([`tests/team1/test_shipment_concurrency_phase_a.py`](file:///d:/7even%20repica%202/tests/team1/test_shipment_concurrency_phase_a.py)):** 8 tests passed.
   - Verified row locks (`SELECT ... FOR UPDATE`), lock ordering (`Shipments` -> `Inventory`), rollback on failure, status transition serialization, and HTTP 409 conflict handling.
2. **`POShipmentAggregationPhaseBTestCase` ([`tests/team2/test_po_shipment_aggregation_phase_b.py`](file:///d:/7even%20repica%202/tests/team2/test_po_shipment_aggregation_phase_b.py)):** 11 tests passed.
   - Verified single-shipment delivery, split-shipment delivery aggregation, mixed status retention, cancellation handling, PO re-activation upon new shipment dispatch, and atomic rollback.
3. **`SplitShipmentReceivingPhaseCTestCase` ([`tests/team1/test_split_shipment_receiving_phase_c.py`](file:///d:/7even%20repica%202/tests/team1/test_split_shipment_receiving_phase_c.py)):** 15 tests passed.
   - Verified split shipment independent progress, multi-product completion, over-receipt prevention, item allocation validation during shipment creation, and legacy fallback safety rules.

### 8.2 Testing Limitations & Categorization
As required by the audit specification, tests are strictly categorized by methodology:
- **Unit Tests Using Mocks:** **34 passed (100%)**. All 34 tests simulate PostgreSQL interactions through custom `MockCursor` and `MockConn` test fixtures.
- **Integration Tests Using Real Database:** **0 tests exist**. The automated test suite does not include integration tests creating records in live Supabase PostgreSQL.
- **Concurrency Tests on Live Database:** **0 tests exist**. While concurrency is simulated using multi-threaded execution against mock objects, real multi-connection PostgreSQL blocking and row-lock behavior has not been tested against live `ShipmentItems` records.
- **Manual Checks Not Yet Performed:**
  - Creating a shipment with explicit product allocations in the live web application (blocked by missing UI form controls).
  - Executing concurrent stock-in requests against a live `ShipmentItems` row in Supabase.

> [!WARNING]
> Passing mocked unit tests confirms code path logic and SQL query construction, but does not substitute for end-to-end frontend transmission or live database integration.

---

## 9. Gap Matrix

| # | Item / Workflow Component | Expected Behavior | Live Reality | Audit Status |
|---|---|---|---|---|
| **G-01** | `ShipmentItems` Live Database Table | Table exists with `BIGSERIAL PK`, FKs, CHECK, UNIQUE, and indexes | Verified present in live Supabase with exact column and constraint types | **PASS** |
| **G-02** | Migration File & Git Status | Migration `003_create_shipment_items.sql` committed to repo | File exists on disk but is **untracked in git**; no DB migration tracking table exists | **PARTIAL** |
| **G-03** | Existing Allocation Data | Past shipments contain allocation rows | **0 rows in `ShipmentItems`**; 65 of 65 shipments are unallocated legacy records | **PASS** (Legacy state verified) |
| **G-04** | Backend Allocation Support (`create_shipment`) | Validates products, caps quantities, locks PO, inserts `ShipmentItems` | Implemented, verified in `shipment_service.py` (lines 805–1098) | **PASS** |
| **G-05** | Backend Stock-In Allocation (`stock_in`) | Enforces shipment allocations, checks receipts, updates receiving status | Implemented, verified in `inventory_service.py` (lines 390–810) | **PASS** |
| **G-06** | Legacy Shipment Safety | Safe fallback for single-shipment POs; rejection of ambiguous splits | Implemented, verified in `inventory_service.py` (lines 487–582) | **PASS** |
| **G-07** | Shipment Details API & UI | Details modal renders allocated products and progress | Implemented and functioning in backend API and `shipments.js` | **PASS** |
| **G-08** | Stock-In Goods Receipt UI | Restricts receiving quantities by remaining allocation | Implemented and functioning in `shipments.js` | **PASS** |
| **G-09** | Create Shipment UI Allocation Inputs | Supplier can select products and allocate quantities for the shipment | **MISSING:** Form has no product or quantity inputs; static text preview only | **MISSING** |
| **G-10** | Create Shipment API Payload Submission | Frontend submits `{ purchase_order_id, ..., items: [{product_id, quantity}] }` | **MISSING:** Payload excludes `items`; backend receives `items: None` | **MISSING** |
| **G-11** | Automated Live Integration Tests | Test suite verifies live database insertion into `ShipmentItems` | **MISSING:** 100% of existing tests rely on in-memory mocks | **NEEDS VERIFICATION** |

---

## 10. Minimal Prioritized Remediation Plan

To bring the SIMS shipment allocation workflow into full end-to-end operational readiness, the following minimal, targeted remediation steps are proposed:

### Priority 1: Version Control Synchronization (Zero Risk)
- **File:** [`database/migrations/003_create_shipment_items.sql`](file:///d:/7even%20repica%202/database/migrations/003_create_shipment_items.sql)
- **Action:** Track and commit the existing migration script to the git repository to ensure schema version-control integrity across environments.

### Priority 2: Frontend Create Shipment Allocation Builder (Core Remediation)
- **File:** [`frontend/js/pages/shipments.js`](file:///d:/7even%20repica%202/frontend/js/pages/shipments.js)
- **Functions:** `openCreateShipmentModal()` (lines 490–646).
- **Required Changes:**
  1. Replace the static text PO preview box with an interactive **Shipment Allocation Table** listing PO line items with:
     - Checkbox or toggle to include/exclude each product in this specific consignment.
     - An integer quantity input prefilled with remaining PO receivable quantity.
     - Maximum quantity cap set to `item.remaining_quantity` (or PO item quantity minus previous non-cancelled allocations).
     - Validation ensuring at least one product is selected and all allocated quantities are > 0 and $\le$ remaining.
  2. Update the `Api.post('/shipments/', ...)` payload construction (line 593) to include:
     ```javascript
     items: selectedItems.map(it => ({
         product_id: it.productId,
         quantity: it.quantity
     }))
     ```

### Priority 3: End-to-End Verification Test
- **Files:** `tests/team2/` or `tests/team1/`
- **Action:** Create a targeted integration test verifying that a shipment created with `items` persists records in `ShipmentItems`, and that subsequent stock-in evaluates against those allocations.

---

## 11. Final Verification Conclusion

### **TABLE EXISTS BUT INTEGRATION IS INCOMPLETE**

The Supabase PostgreSQL database table `public."ShipmentItems"` and the backend service/API architecture are fully ready and functional. However, because the frontend **Create Shipment** modal does not include line-item allocation inputs and omits the `items` payload during submission, all dispatches created by users continue to bypass `ShipmentItems` entirely, leaving the live table at 0 records. Remediation of the Create Shipment UI is required to complete the end-to-end integration.
