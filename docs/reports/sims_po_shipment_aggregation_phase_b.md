# SIMS — Purchase Order Status Aggregation for Split Shipments (Phase B Remediation Report)

**Repository:** `EDI-SIMS` (Smart Inventory Management System)  
**Date:** October 18, 2026  
**Auditor & Implementation Agent:** DeepMind Advanced Agentic Coding Pair  
**Related Audit:** `docs/reports/sims_shipment_status_lifecycle_audit.md`  
**Related Phase A Report:** `docs/reports/sims_shipment_remediation_phase_a.md`  
**Status:** **RESOLVED & VERIFIED**

---

## 1. Executive Summary

In the baseline implementation of SIMS, marking any individual shipment as `Delivered` executed an unconditional update:
```sql
UPDATE "PurchaseOrders" SET status = 'Delivered' WHERE purchase_order_id = %s
```
This created a severe business integrity defect (Defect #3 from the Shipment Lifecycle Audit): when an order was split across multiple consignments, the delivery of the *first* partial shipment prematurely changed the entire parent Purchase Order to `Delivered`. This obscured outstanding consignments, allowed premature supplier invoice generation for incomplete deliveries, and corrupted procurement reporting.

Phase B resolves this defect by introducing **Aggregation-Aware Purchase Order Status Recalculation** backed by serialized row-level locking on `PurchaseOrders`.

---

## 2. Business Rules & State Logic

### 2.1 The Aggregation Rule
A Purchase Order must **not** be marked `Delivered` until all relevant shipments associated with that Purchase Order have reached the required `Delivered` state:

$$\text{PO Status} = \begin{cases} 
\text{'Delivered'}, & \text{if } N_{\text{total}} > 0 \land N_{\text{delivered}} = N_{\text{total}} \\
\text{'Accepted'}, & \text{if } N_{\text{delivered}} < N_{\text{total}} \land \text{Current PO Status} \in \{\text{'Accepted'}, \text{'Delivered'}\} \\
\text{Unchanged}, & \text{if } \text{Current PO Status} \notin \{\text{'Accepted'}, \text{'Delivered'}\} 
\end{cases}$$

Where:
- $N_{\text{total}}$ is the total number of shipments created for the PO.
- $N_{\text{delivered}}$ is the number of shipments in status `'Delivered'`.

### 2.2 Status Matrix & Edge Case Handling

| Scenario | Shipment 1 Status | Shipment 2 Status | Shipment 3 Status | PO Current Status | Target PO Status | Explanation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Single Shipment** | `In Transit` $\to$ `Delivered` | *N/A* | *N/A* | `Accepted` | `Delivered` | 1/1 delivered. Matches existing single-consignment workflow. |
| **Split Dispatches** | `Delivered` | `In Transit` | *N/A* | `Accepted` | `Accepted` | 1/2 delivered. Consignment 2 outstanding; PO remains in active fulfillment. |
| **Final Delivery** | `Delivered` | `In Transit` $\to$ `Delivered` | *N/A* | `Accepted` | `Delivered` | 2/2 delivered. All shipments delivered; PO transitions to `Delivered`. |
| **Delayed Shipment** | `Delivered` | `Delayed` | *N/A* | `Accepted` | `Accepted` | 1/2 delivered. Consignment 2 is delayed; PO remains `Accepted`. |
| **Cancelled Consignment** | `Delivered` | `Cancelled` | *N/A* | `Accepted` | `Accepted` | A cancelled shipment does **not** count as delivered. Full order delivery was not fulfilled. |
| **All Cancelled** | `Cancelled` | `Cancelled` | *N/A* | `Accepted` | `Accepted` | 0/2 delivered. PO remains `Accepted`. |
| **Fulfillment Resumption**| `Delivered` | *New Shipment Created* (`In Transit`) | *N/A* | `Delivered` | `Accepted` | When a new shipment is dispatched for an already-delivered PO, PO status is resumed to `Accepted`. |
| **Unrelated State (Rejected)** | `In Transit` $\to$ `Delivered` | *N/A* | *N/A* | `Rejected` | `Rejected` | Preserved strictly. Shipment lifecycle changes cannot overwrite a rejected procurement order. |
| **Unrelated State (Pending)** | `In Transit` $\to$ `Delivered` | *N/A* | *N/A* | `Pending` | `Pending` | Preserved strictly. Pending supplier decision is never overwritten. |

### 2.3 Evaluation of `Partially Delivered` Status
- **Schema & Codebase Audit:** Inspection of the PostgreSQL schema and all routes (`backend/app/routes/`) confirmed that neither `PurchaseOrders.status` nor frontend dropdowns recognize `Partially Delivered`. Valid recognized states across all modules are `Pending`, `Accepted`, `Rejected`, and `Delivered`.
- **Decision:** Inventing an ad-hoc `'Partially Delivered'` status without a database migration would break frontend filters (`purchase-orders.js`) and invoice validation (`supplier_invoice_service.py`). Therefore, `'Accepted'` is strictly preserved to represent active procurement fulfillment in progress, aligning with existing SIMS business rules.

---

## 3. Concurrency & Deadlock-Free Locking Architecture

### 3.1 Lock Acquisition Hierarchy
To prevent race conditions between concurrent status updates on split shipments of the same PO without introducing deadlocks, a strict hierarchical locking order is enforced:

1. **Step 1:** Lock the target shipment row:
   ```sql
   SELECT ... FROM "Shipments" shp
   JOIN "Suppliers" s ON shp.supplier_id = s.supplier_id
   WHERE shp.shipment_id = %s
   FOR UPDATE OF shp;
   ```
2. **Step 2:** Lock the parent Purchase Order row:
   ```sql
   SELECT purchase_order_id, status
   FROM "PurchaseOrders"
   WHERE purchase_order_id = %s
   FOR UPDATE;
   ```
3. **Step 3:** Perform conditional shipment update:
   ```sql
   UPDATE "Shipments"
   SET status = %s, shipped_at = %s, delivered_at = %s, updated_at = NOW()
   WHERE shipment_id = %s AND status = %s;
   ```
4. **Step 4:** Query all shipments for the PO under the PO row lock:
   ```sql
   SELECT shipment_id, status
   FROM "Shipments"
   WHERE purchase_order_id = %s;
   ```
5. **Step 5:** Conditionally update Purchase Order status and record audit entries:
   ```sql
   UPDATE "PurchaseOrders" SET status = %s WHERE purchase_order_id = %s;
   ```

### 3.2 Deadlock Prevention Proof
- **No Circular Waits:** All operations touching both `Shipments` and `PurchaseOrders` acquire locks in the exact order $\text{Shipments} \to \text{PurchaseOrders}$.
- **Isolation of Split Shipments:** If Thread 1 updates Shipment 1 and Thread 2 updates Shipment 2 (both for PO 50):
  - Thread 1 locks Shipment 1, then acquires the lock on PO 50.
  - Thread 2 locks Shipment 2, then waits on the lock on PO 50.
  - Thread 1 never requests Shipment 2; Thread 2 never requests Shipment 1.
  - The resource allocation graph is acyclic ($\text{Shipment 1} \to \text{PO 50}$, $\text{Shipment 2} \to \text{PO 50}$), preventing deadlocks.
  - Once Thread 1 commits, Thread 2 acquires PO 50 and evaluates the fresh, committed state of all shipments.

---

## 4. Audit Trail, Notifications & Downstream Consistency

### 4.1 OrderStatusHistory Logging
When the Purchase Order status changes as a result of shipment aggregation, explicit PO-level history records are inserted:
- **Transition to Delivered:** Action `ORDER_DELIVERED` with note: `All N shipment(s) delivered. Purchase order marked Delivered.`
- **Resumption of Fulfillment:** Action `ORDER_FULFILLMENT_RESUMED` with note: `Shipment status updated. Purchase order retained in Accepted status (X/Y delivered).`

### 4.2 AuditLog Compliance
Every PO status transition automatically calls `log_audit_event`:
```python
log_audit_event(
    action='PO_STATUS_CHANGED',
    table_name='PurchaseOrders',
    record_id=po_id,
    user_id=int(user_id) if user_id else None,
    cursor=cursor
)
```

### 4.3 Downstream Integrity
- **Supplier Invoices:** `supplier_invoice_service.py` requires `Shipments.status == 'Delivered'` and `PurchaseOrders.status == 'Delivered'`. Invoicing is now safely blocked until 100% of consignments are delivered.
- **Stock Receiving:** `inventory_service.py` (`POST /api/inventory/stock-in`) requires shipment-level `Delivered` status and enforces its own row-level locks on `Shipments` and `Inventory`. Partial deliveries can be received at the warehouse while the PO remains `Accepted`.

---

## 5. Verification & Test Results

A test suite comprising 12 new dedicated tests in `tests/team2/test_po_shipment_aggregation_phase_b.py` and 12 regression tests in `tests/team1/test_shipment_concurrency_phase_a.py` was executed:

| Test Case | Objective | Result |
| :--- | :--- | :--- |
| `test_01_single_shipment_delivered_sets_po_delivered` | Single shipment PO transitions from Accepted to Delivered upon delivery | **PASSED** |
| `test_02_split_shipments_first_delivered_keeps_po_accepted` | First shipment delivered while second is In Transit leaves PO as Accepted | **PASSED** |
| `test_03_split_shipments_all_delivered_sets_po_delivered` | Second and final shipment delivered transitions PO to Delivered | **PASSED** |
| `test_04_split_shipments_mix_with_delayed_keeps_po_accepted` | Delivered + Delayed shipments leaves PO as Accepted | **PASSED** |
| `test_05_cancelled_shipment_does_not_count_as_delivered` | Cancelled shipment does not count as delivered; Delivered + Cancelled keeps PO Accepted | **PASSED** |
| `test_06_all_cancelled_shipments_leaves_po_accepted` | All-cancelled shipments leave PO in Accepted status | **PASSED** |
| `test_07_unrelated_po_state_rejected_preserved` | Rejected PO status is strictly preserved and never overwritten | **PASSED** |
| `test_08_unrelated_po_state_pending_preserved` | Pending PO status is strictly preserved and never overwritten | **PASSED** |
| `test_09_adding_shipment_to_delivered_po_resumes_accepted` | Dispatching new active shipment for a Delivered PO resumes PO to Accepted | **PASSED** |
| `test_10_concurrent_updates_to_separate_shipments_same_po` | Concurrent updates to separate shipments serialize cleanly via PO FOR UPDATE lock | **PASSED** |
| `test_11_failed_aggregation_rolls_back_atomically` | Simulated DB error during PO aggregation rolls back shipment and PO atomically | **PASSED** |
| `test_12_phase_a_shipment_concurrency_locks_preserved` | Phase A row locks (`FOR UPDATE OF shp`) and conditional updates remain intact | **PASSED** |
| Phase A Concurrency Suite (12 tests) | Terminal state checks, optimistic conflict detection (409), stock-in locking | **PASSED** (12/12) |

**Overall Result:** **24 passed, 0 failed in 56.53s (100% Pass Rate)**

---

## 6. Files Modified

1. `backend/app/services/team2/shipment_service.py`:
   - Updated `update_shipment_status()`: Replaced unconditional PO update with row-level locked aggregation calculation, `OrderStatusHistory` logging, and audit tracking.
   - Updated `create_shipment()`: Added `FOR UPDATE` lock on `PurchaseOrders` and automatic resumption of PO status to `Accepted` if a new active shipment is created for a previously `Delivered` PO.
2. `tests/team1/test_shipment_concurrency_phase_a.py`:
   - Aligned MockCursor to support multi-table queries and safe string casting.
3. `tests/team2/test_po_shipment_aggregation_phase_b.py`:
   - Added 12 comprehensive unit and concurrency regression tests for Phase B.
