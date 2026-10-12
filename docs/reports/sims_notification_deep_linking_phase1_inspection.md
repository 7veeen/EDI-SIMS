# SIMS Improvement 4 — Notification Deep-Linking
## Phase 1: Codebase Inspection and Gap Analysis Report

**Document ID:** `SIMS-NOTIF-PHASE1-INSPECTION`  
**Execution Date:** 2026-10-12  
**Lifecycle Stage:** Phase 1 (Inspection & Gap Analysis — Strictly Read-Only)  
**Target Module:** Notification System & SPA Cross-Module Deep-Linking  
**System:** Smart Inventory Management System (SIMS)  
**Status:** **INSPECTION COMPLETE — STOPPED FOR APPROVAL**

---

## 1. Executive Summary

This report delivers the Phase 1 Codebase Inspection and Gap Analysis for **Notification Deep-Linking** in the Smart Inventory Management System (SIMS). The inspection evaluated how user notifications navigate to underlying business entity records across the Single Page Application (SPA), identifying precisely which reference types succeed, which partially navigate, and which fail completely.

### High-Level Findings
1. **Critical Function:** All notification navigation logic is centralized in a single client-side function: `App.navigateToReference(referenceType, referenceId, notificationId = null)` in [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js#L460-L535).
2. **Supported in Code vs. Reality:** Current code only attempts to handle `Shipment`, `PurchaseOrder`, and `Product`. 
   - `SupplierQuotation` and `StockRequest` are **completely unhandled**, silently falling back to the generic `#notifications` page.
3. **Database Casing Mismatch (227 broken notifications):** Live Supabase catalog inspection revealed that 227 historical notification records use uppercase/snake_case types (`SHIPMENT`, `PURCHASE_ORDER`, `PRODUCT`, `QUOTATION`). Because `App.navigateToReference` performs strict case-sensitive checks (`=== 'Shipment'`), **all uppercase records fail to navigate and fall back to `#notifications`**.
4. **Product Search Defect (False Deep-Link):** For `Product`, navigation routes to `#products` and sets the search query to the integer `reference_id` (e.g. `1`). However, backend [`backend/app/services/team1/product_service.py`](file:///d:/7even/repica/2/backend/app/services/team1/product_service.py#L18) only filters `product_name` and `sku`, not `product_id`. Consequently, searching by ID yields 0 results instead of locating the target product, and the product edit modal is never invoked.
5. **Purchase Order Incomplete Navigation:** For `PurchaseOrder`, navigation sets the search input on `#purchase-orders` instead of directly opening the comprehensive detail modal (`App.pages['purchase-orders'].viewPODetails(poId)`), which already exists in the codebase.
6. **Zero Migration / Zero Live Mutation:** In strict compliance with constraints, this inspection was 100% read-only. No live records were altered, no migrations executed, and no source code modified.

---

## 2. Files and Functions Inspected

### 2.1 Frontend Files & Controllers
- [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js):
  - `App.routes` (lines 6–25): Central route registry with icon, label, and allowed RBAC roles.
  - `App.navigate(path)` (lines 172–205): Role verification guard, hash routing, and page container mounting.
  - `App.notifications.init()` & `loadRecent()` (lines 280–428): Topbar dropdown component, unread counter pill, and dropdown item click listener (`item.addEventListener('click', ... App.navigateToReference(...))`).
  - `App.navigateToReference(referenceType, referenceId, notificationId = null)` (lines 460–535): Target deep-link resolution and execution logic.
- [`frontend/js/pages/notifications.js`](file:///d:/7even/repica/2/frontend/js/pages/notifications.js):
  - `App.pages['notifications'].renderTable(notifications)` (lines 340–400): Renders notification table rows, embedding `App.navigateToReference` on title links (line 350) and "View" action buttons (line 387).
  - `App.pages['notifications'].markAsRead(notificationId)` (lines 420–445): Individual mark-read handler.
- [`frontend/js/pages/shipments.js`](file:///d:/7even/repica/2/frontend/js/pages/shipments.js):
  - `App.pages['shipments'].openShipmentDetailsModal(shipmentId)` (lines 749–850): Modal detail view with timeline and receiving controls.
- [`frontend/js/pages/purchase-orders.js`](file:///d:/7even/repica/2/frontend/js/pages/purchase-orders.js):
  - `App.pages['purchase-orders'].viewPODetails(poId)` (lines 270–440): Modal detail view for purchase orders.
  - `App.pages['purchase-orders'].loadPurchaseOrders(search)`: Table search loader.
- [`frontend/js/pages/products.js`](file:///d:/7even/repica/2/frontend/js/pages/products.js):
  - `App.pages['products'].showProductModal(productId)` (lines 306–380): Modal detail and edit view for products.
  - `App.pages['products'].loadProducts()`: Table search loader.
- [`frontend/js/pages/quotations.js`](file:///d:/7even/repica/2/frontend/js/pages/quotations.js):
  - `App.pages['quotations'].openQuotationDetailsModal(quotationId)` (lines 668–750): Modal detail view comparing quotation bids.
- [`frontend/js/pages/stock-requests.js`](file:///d:/7even/repica/2/frontend/js/pages/stock-requests.js):
  - `App.pages['stock-requests'].openDetailsModal(stockRequestId)` (lines 522–600): Modal detail view for procurement stock requests.
- [`frontend/js/pages/payments.js`](file:///d:/7even/repica/2/frontend/js/pages/payments.js):
  - `App.pages['payments'].openViewInvoiceModal(invoiceId)`: Modal detail view for supplier invoices.
  - `App.pages['payments'].openViewPaymentModal(paymentId)`: Modal detail view for disbursement ledger entries.
- [`frontend/js/pages/stock-transactions.js`](file:///d:/7even/repica/2/frontend/js/pages/stock-transactions.js):
  - `App.pages['stock-transactions']`: Table view for stock movements.

### 2.2 Backend Files & Services
- [`backend/app/services/team3/notification_service.py`](file:///d:/7even/repica/2/backend/app/services/team3/notification_service.py):
  - `create_notification(...)` (lines 332–480): Creates notifications with duplicate suppression; stores `reference_type` and `reference_id`.
  - `get_notifications_for_user(...)` (lines 15–90): Enforces strict user isolation.
- [`backend/app/routes/team3/notifications.py`](file:///d:/7even/repica/2/backend/app/routes/team3/notifications.py):
  - Route handlers for `/api/notifications/`, `/unread-count`, `/read-all`, and `/<id>/read`.
- [`backend/app/services/team2/shipment_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/shipment_service.py):
  - Triggers notifications with `reference_type="Shipment"`, `reference_id=shipment_id` on employee assignment and delivery.
- [`backend/app/services/team2/purchase_order_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/purchase_order_service.py):
  - Triggers notifications with `reference_type="PurchaseOrder"`, `reference_id=po_id` on supplier response.
- [`backend/app/services/team2/quotation_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/quotation_service.py):
  - Triggers notifications with `reference_type="PurchaseOrder"`, `reference_id=po_id` on quotation submission and approval/rejection.
- [`backend/app/services/team2/stock_request_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/stock_request_service.py):
  - Triggers notifications with `reference_type="StockRequest"`, `reference_id=stock_request_id` (line 546).
- [`backend/app/services/team1/inventory_service.py`](file:///d:/7even/repica/2/backend/app/services/team1/inventory_service.py):
  - Triggers notifications with `reference_type="Product"`, `reference_id=product_id` on low stock.
  - Triggers notifications with `reference_type="Shipment"`, `reference_id=shipment_id` on stock-in.
- [`backend/app/services/team1/product_service.py`](file:///d:/7even/repica/2/backend/app/services/team1/product_service.py):
  - `get_products` (line 18): Confirmed backend SQL search parameter does not include `product_id`.

### 2.3 Test Files Inspected
- [`scratch/test_browser_step7c.py`](file:///d:/7even/repica/2/scratch/test_browser_step7c.py#L284-L315): Prior automated browser test suite (TC-13, 14, 15) testing `navigateToReference` for Shipment, PurchaseOrder, Product by asserting URL hash only.
- [`tests/team3/test_dashboard.py`](file:///d:/7even/repica/2/tests/team3/test_dashboard.py): Notification assertions in dashboard payload.

---

## 3. Existing Notification Reference Types and Database Distribution

A read-only catalog query on `public."Notifications"` in the live database identified **657 total notification records**:

| `reference_type` in Database | Total Count | Has Valid `reference_id` | Null `reference_id` | Sample `reference_id` Range | Common Notification Types |
|---|---|---|---|---|---|
| `Shipment` | 198 | 198 | 0 | 19 – 54 | `Shipment Delivered`, `Stock-In`, `Shipment Assignment` |
| `PurchaseOrder` | 117 | 117 | 0 | 10 – 101 | `Quotation Submitted`, `PO Accepted`, `Quotation Approved` |
| `PURCHASE_ORDER` | 82 | 82 | 0 | 40 – 57 | `PO_ACCEPTED`, `PO_CREATED`, `PO_REJECTED` |
| `SHIPMENT` | 63 | 63 | 0 | 1 – 7 | `SHIPMENT_DELIVERED`, `SHIPMENT_DISPATCHED`, `EMPLOYEE_ASSIGNED` |
| `QUOTATION` | 58 | 58 | 0 | 27 – 38 | `QUOTATION_SUBMITTED`, `QUOTATION_APPROVED`, `QUOTATION_REJECTED` |
| `Product` | 35 | 35 | 0 | 24 – 28 | `Low Stock` |
| `PRODUCT` | 24 | 24 | 0 | 1 | `LOW_STOCK` |
| `TRANSACTION` | 8 | 8 | 0 | 23 – 30 | `STOCK_IN` |
| `None` (NULL) | 20 | 0 | 20 | NULL | `SYSTEM`, `PO_CREATED`, `EMPLOYEE_ASSIGNED` |
| Test Records (`DuplicateRef`, `TestPO`, `TestTask`, `T1`, `T2`, `T3`) | 45 | 45 | 0 | Unix timestamps | Test alert suites |
| **Total** | **657** | **637** | **20** | — | — |

> [!IMPORTANT]
> **Key Database Findings:**
> 1. `QUOTATION` stores `reference_id` pointing directly to `public."SupplierQuotations".quotation_id`.
> 2. `StockRequest` is actively produced by `stock_request_service.py` when suppliers respond to requests, but historical test records in this sample were zero.
> 3. Casing variance is substantial: 227 records (35% of all referenced records) use uppercase/snake_case formatting (`SHIPMENT`, `PURCHASE_ORDER`, `PRODUCT`, `QUOTATION`).

---

## 4. Evaluation of Reference Types (Detailed Gap Analysis)

### 4.1 Shipment (`Shipment` / `SHIPMENT`)
- **Storage:** `reference_type` = `'Shipment'` or `'SHIPMENT'`, `reference_id` = integer `shipment_id`.
- **Target Route:** `#shipments` (Roles permitted: `Owner`, `Manager`, `Supplier`, `Employee`).
- **Detail Modal Available:** `App.pages['shipments'].openShipmentDetailsModal(shipmentId)` exists and fetches `/api/shipments/<id>`.
- **Current Behavior:**
  - `refType === 'Shipment'`: Navigates to `#shipments`, displays toast, and invokes `openShipmentDetailsModal(refId)` after 400ms. **Works for lowercase/PascalCase.**
  - `refType === 'SHIPMENT'`: Fails strict equality check (`=== 'Shipment'`). Falls back to `#notifications`. **BROKEN (63 records).**
- **RBAC:** All 4 roles are permitted on `#shipments`. Backend `/api/shipments/<id>` validates role-specific access (supplier isolation, assigned employee verification).
- **Missing Record Handling:** Handled safely via `try/catch` in `openShipmentDetailsModal`.

### 4.2 Purchase Order (`PurchaseOrder` / `PURCHASE_ORDER`)
- **Storage:** `reference_type` = `'PurchaseOrder'` or `'PURCHASE_ORDER'`, `reference_id` = integer `purchase_order_id`.
- **Target Route:** `#purchase-orders` (Roles permitted: `Owner`, `Manager`, `Supplier`. `Employee` denied).
- **Detail Modal Available:** `App.pages['purchase-orders'].viewPODetails(poId)` exists and fetches `/api/purchase-orders/<id>`.
- **Current Behavior:**
  - `refType === 'PurchaseOrder'`: Navigates to `#purchase-orders`, populates the search input `#po-search` with `refId`, and calls `loadPurchaseOrders()`. **DOES NOT OPEN MODAL.**
  - `refType === 'PURCHASE_ORDER'`: Fails strict equality check (`=== 'PurchaseOrder'`). Falls back to `#notifications`. **BROKEN (82 records).**
- **RBAC:** If an `Employee` clicks a PO notification, `App.navigateToReference` displays a warning toast: `"Purchase Orders are restricted to Managers, Owners, and Suppliers"`. Safe.
- **Missing Record Handling:** If `viewPODetails` is invoked with a non-existent ID, it catches the 404 and displays `Utils.showToast("Failed to load PO details: " + err.message, "error")`.

### 4.3 Product (`Product` / `PRODUCT`)
- **Storage:** `reference_type` = `'Product'` or `'PRODUCT'`, `reference_id` = integer `product_id`.
- **Target Route:** `#products` (Roles permitted: `Owner`, `Manager`, `Employee`. `Supplier` denied).
- **Detail Modal Available:** `App.pages['products'].showProductModal(productId)` exists and fetches `/api/products/<id>`.
- **Current Behavior:**
  - `refType === 'Product'`: Navigates to `#products`, sets `this.pages['products'].search = String(refId)`, sets `#product-search` value, and calls `loadProducts()`. **DOES NOT OPEN MODAL.**
  - **CRITICAL BACKEND SEARCH DEFECT:** In [`backend/app/services/team1/product_service.py`](file:///d:/7even/repica/2/backend/app/services/team1/product_service.py#L18), search is defined as:
    ```python
    if search:
        base_where += ' AND (p.product_name ILIKE %s OR p.sku ILIKE %s)'
        params.extend([f"%{search}%", f"%{search}%"])
    ```
    The search filter checks *only* `product_name` and `sku`. It does *not* query `product_id`. As a result, searching for `1` returns products that happen to have "1" in their name or SKU, or 0 products if none match. The target product is not selected.
  - `refType === 'PRODUCT'`: Fails strict equality check. Falls back to `#notifications`. **BROKEN (24 records).**
- **RBAC:** `Supplier` role is blocked by route guard with toast: `"Products module is not accessible for role Supplier"`. Safe.
- **Missing Record Handling:** Handled safely in `showProductModal` via `try/catch` and error toast.

### 4.4 Supplier Quotation (`SupplierQuotation` / `QUOTATION` / `Quotation`)
- **Storage:** `reference_type` = `'QUOTATION'` or `'SupplierQuotation'`, `reference_id` = integer `quotation_id`.
- **Target Route:** `#quotations` (Roles permitted: `Owner`, `Manager`, `Supplier`. `Employee` denied).
- **Detail Modal Available:** `App.pages['quotations'].openQuotationDetailsModal(quotationId)` exists in [`frontend/js/pages/quotations.js`](file:///d:/7even/repica/2/frontend/js/pages/quotations.js#L668-L750).
- **Current Behavior:** **COMPLETELY BROKEN.**
  - Not present in `App.navigateToReference` if-else branches.
  - Falls through to `else { window.location.hash = 'notifications'; }`.
  - Result: When a user clicks a Quotation notification, the notification is marked read, but the UI remains on the notification page without opening the quotation or navigating to `#quotations`.
- **RBAC:** `#quotations` route restricts access to `Owner`, `Manager`, `Supplier`. `Employee` is blocked.
- **Missing Record Handling:** `openQuotationDetailsModal` handles missing quotations via `try/catch`.

### 4.5 Stock Request (`StockRequest` / `STOCK_REQUEST`)
- **Storage:** `reference_type` = `'StockRequest'` or `'STOCK_REQUEST'`, `reference_id` = integer `stock_request_id`.
- **Target Route:** `#stock-requests` (Roles permitted: `Owner`, `Manager`, `Supplier`. `Employee` denied).
- **Detail Modal Available:** `App.pages['stock-requests'].openDetailsModal(stockRequestId)` exists in [`frontend/js/pages/stock-requests.js`](file:///d:/7even/repica/2/frontend/js/pages/stock-requests.js#L522-L600).
- **Current Behavior:** **COMPLETELY BROKEN.**
  - Not present in `App.navigateToReference` if-else branches.
  - Falls through to `else { window.location.hash = 'notifications'; }`.
  - Result: When a Manager/Owner receives a `"Stock Request Updated"` notification and clicks "View", nothing opens.
- **RBAC:** `#stock-requests` route restricts access to `Owner`, `Manager`, `Supplier`. `Employee` is blocked.
- **Missing Record Handling:** `openDetailsModal` handles missing records via `if (!sr) Utils.showToast('Stock request details could not be found.', 'error');`.

### 4.6 Stock Movement Transaction (`StockTransaction` / `TRANSACTION`)
- **Storage:** `reference_type` = `'TRANSACTION'`, `reference_id` = integer `transaction_id`.
- **Target Route:** `#stock-transactions` (Roles permitted: `Owner`, `Manager`, `Employee`. `Supplier` denied).
- **Detail View:** Table view with search `#tx-search-input`.
- **Current Behavior:** **COMPLETELY BROKEN.** Not handled in `App.navigateToReference`. Falls through to `#notifications`.

---

## 5. Verified Working vs. Broken / Incomplete Matrix

| Reference Type | Format Variants in DB / Code | Target Route | Target Action / Modal Function | Current Status | Root Cause of Failure / Gap |
|---|---|---|---|---|---|
| **Shipment** | `Shipment` | `#shipments` | `openShipmentDetailsModal(id)` | **WORKING** | Opens modal after 400ms delay. |
| **Shipment** | `SHIPMENT` | `#shipments` | `openShipmentDetailsModal(id)` | **BROKEN** | Strict case comparison `refType === 'Shipment'` fails. |
| **Purchase Order** | `PurchaseOrder` | `#purchase-orders` | `viewPODetails(id)` | **INCOMPLETE** | Only filters table via `#po-search`; does not open detail modal. |
| **Purchase Order** | `PURCHASE_ORDER` | `#purchase-orders` | `viewPODetails(id)` | **BROKEN** | Strict case comparison fails; falls back to `#notifications`. |
| **Product** | `Product` | `#products` | `showProductModal(id)` | **BROKEN / DEFECTIVE** | Sets search to integer ID, but backend search doesn't query ID; modal not opened. |
| **Product** | `PRODUCT` | `#products` | `showProductModal(id)` | **BROKEN** | Strict case comparison fails; falls back to `#notifications`. |
| **Supplier Quotation** | `SupplierQuotation`, `QUOTATION`, `Quotation` | `#quotations` | `openQuotationDetailsModal(id)` | **COMPLETELY BROKEN** | Completely missing from `App.navigateToReference`. |
| **Stock Request** | `StockRequest`, `STOCK_REQUEST` | `#stock-requests` | `openDetailsModal(id)` | **COMPLETELY BROKEN** | Completely missing from `App.navigateToReference`. |
| **Stock Transaction** | `TRANSACTION`, `StockTransaction` | `#stock-transactions` | Search `#tx-search-input` / table | **COMPLETELY BROKEN** | Completely missing from `App.navigateToReference`. |
| **Null / Missing Ref** | `None` / `null` / `""` | `#notifications` | None | **SAFE FALLBACK** | Correctly remains on notifications page. |

---

## 6. Role and Permission Checks (RBAC)

The existing route definitions in `App.routes` enforce strict role boundaries:

```javascript
{ path: 'stock-requests', roles: ['Owner', 'Manager', 'Supplier'] },
{ path: 'quotations', roles: ['Owner', 'Manager', 'Supplier'] },
{ path: 'products', roles: ['Owner', 'Manager', 'Employee'] },
{ path: 'purchase-orders', roles: ['Owner', 'Manager', 'Supplier'] },
{ path: 'shipments', roles: ['Owner', 'Manager', 'Supplier', 'Employee'] },
{ path: 'stock-transactions', roles: ['Owner', 'Manager', 'Employee'] },
{ path: 'payments', roles: ['Owner', 'Manager', 'Supplier'] },
{ path: 'notifications', roles: ['Owner', 'Manager', 'Employee', 'Supplier'] }
```

### RBAC Cross-Matrix for Deep-Link Navigation:
| Entity / Reference Type | Owner | Manager | Supplier | Employee | Access Guard Mechanism |
|---|:---:|:---:|:---:|:---:|---|
| **Shipment** | Allowed | Allowed | Allowed (own) | Allowed (assigned) | Route guard + Backend row-level checks |
| **Purchase Order** | Allowed | Allowed | Allowed (own) | **DENIED** | Route guard: Toast `"Purchase Orders are restricted..."` |
| **Product** | Allowed | Allowed | **DENIED** | Allowed | Route guard: Toast `"Products module is not accessible..."` |
| **Supplier Quotation** | Allowed | Allowed | Allowed (own) | **DENIED** | Route guard: Toast `"Quotations module is not accessible..."` |
| **Stock Request** | Allowed | Allowed | Allowed (own) | **DENIED** | Route guard: Toast `"Stock Requests module is not accessible..."` |
| **Stock Transaction** | Allowed | Allowed | **DENIED** | Allowed | Route guard: Toast `"Stock Transactions module is not accessible..."` |

> [!NOTE]
> All destination routes already reject unauthorized roles both in the frontend route registry (`App.navigate`) and in the backend Flask `@role_required` decorators. When deep-linking, `App.navigateToReference` must verify `route.roles.includes(user.role)` before changing `window.location.hash`, and display a descriptive warning toast if blocked.

---

## 7. Missing-Record and Unsupported-Reference Behavior

### 7.1 Notification Mark-Read Behavior (Preserved)
- In `App.navigateToReference`, lines 461–471:
  ```javascript
  if (notificationId) {
      try {
          await Api.markNotificationRead(notificationId);
          await this.notifications.updateUnreadCount();
          if (window.location.hash.includes('notifications') && this.pages['notifications'] && this.pages['notifications'].loadNotifications) {
              this.pages['notifications'].loadNotifications();
          }
      } catch (e) {
          // Ignore silent read errors during navigation
      }
  }
  ```
- **Finding:** Clicking any notification marks it as read immediately and updates the unread badge counter. This behavior functions correctly and **must be preserved** regardless of whether navigation succeeds.

### 7.2 Missing or Null Reference
- If `!referenceType || !referenceId`:
  - `window.location.hash = 'notifications'; return;`
  - Correctly prevents broken routing, but provides no visual feedback.

### 7.3 Unsupported Reference Types
- Currently falls through to `else { window.location.hash = 'notifications'; }`.
- **Finding:** Silent fallback causes user confusion because clicking "View" gives no indication that the entity type cannot be opened.

### 7.4 Non-Existent or Deleted Entity Record (e.g. ID not in DB)
- All target modal functions (`openShipmentDetailsModal`, `viewPODetails`, `openQuotationDetailsModal`, `openDetailsModal`, `showProductModal`) execute `Api.get(...)` inside `try/catch` blocks.
- If the backend returns HTTP 404, the catch blocks display an error toast or alert without crashing the SPA shell.

---

## 8. Minimal Recommended Code Changes (Phase 2 Architecture)

All required changes are localized to **a single file**: [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js). No backend schema modifications or framework additions are necessary.

### 8.1 Proposed Normalization & Dispatcher Design
Refactor `App.navigateToReference` to include:
1. **Case-Insensitive Reference Normalizer:**
   ```javascript
   const rawType = (referenceType || '').trim().toUpperCase().replace(/[\s_-]+/g, '');
   // Maps 'SHIPMENT' -> 'SHIPMENT'
   // Maps 'PURCHASE_ORDER' -> 'PURCHASEORDER'
   // Maps 'PRODUCT' -> 'PRODUCT'
   // Maps 'QUOTATION' or 'SUPPLIERQUOTATION' -> 'QUOTATION'
   // Maps 'STOCKREQUEST' or 'STOCK_REQUEST' -> 'STOCKREQUEST'
   // Maps 'TRANSACTION' or 'STOCKTRANSACTION' -> 'STOCKTRANSACTION'
   ```
2. **Unified Action Map:**
   Define clean mappings from normalized type to route, role verification, and direct modal trigger:
   - `'SHIPMENT'`: route `'shipments'`, calls `App.pages['shipments'].openShipmentDetailsModal(refId)`
   - `'PURCHASEORDER'`: route `'purchase-orders'`, calls `App.pages['purchase-orders'].viewPODetails(refId)`
   - `'PRODUCT'`: route `'products'`, calls `App.pages['products'].showProductModal(refId)`
   - `'QUOTATION'`: route `'quotations'`, calls `App.pages['quotations'].openQuotationDetailsModal(refId)`
   - `'STOCKREQUEST'`: route `'stock-requests'`, calls `App.pages['stock-requests'].openDetailsModal(refId)`
   - `'STOCKTRANSACTION'`: route `'stock-transactions'`, filters `#tx-search-input`
3. **Safe Navigation Helper:**
   Execute route hash update, verify role authorization, display informative toast, and cleanly dispatch the detail modal once the target page controller is loaded.
4. **Descriptive Fallback:**
   If a reference type remains unrecognized, display a clear user notice (`Utils.showToast("Direct link unavailable for reference type: " + referenceType, "warning")`) while remaining safely on the notifications list.

---

## 9. Focused Tests Required for Phase 2

To ensure complete coverage without regression, the following automated test cases should be implemented in Phase 2:

1. **Test Normalization Logic:**
   - Verify that `'Shipment'`, `'SHIPMENT'`, and `'shipment'` resolve to `'shipments'`.
   - Verify that `'PurchaseOrder'`, `'PURCHASE_ORDER'`, and `'purchase_order'` resolve to `'purchase-orders'`.
   - Verify that `'Product'`, `'PRODUCT'`, and `'product'` resolve to `'products'`.
   - Verify that `'Quotation'`, `'QUOTATION'`, and `'SupplierQuotation'` resolve to `'quotations'`.
   - Verify that `'StockRequest'`, `'STOCK_REQUEST'`, and `'stock_request'` resolve to `'stock-requests'`.
2. **Test Modal Invocation:**
   - Verify `openShipmentDetailsModal` is called with target ID when navigating to Shipment.
   - Verify `viewPODetails` is called with target ID when navigating to PurchaseOrder.
   - Verify `showProductModal` is called with target ID when navigating to Product.
   - Verify `openQuotationDetailsModal` is called with target ID when navigating to Quotation.
   - Verify `openDetailsModal` is called with target ID when navigating to StockRequest.
3. **Test Role Enforcement:**
   - Verify Employee clicking PurchaseOrder, Quotation, or StockRequest is blocked with descriptive toast and does not change route.
   - Verify Supplier clicking Product or StockTransaction is blocked with descriptive toast.
4. **Test Read Status Mutation:**
   - Verify `Api.markNotificationRead(notificationId)` is executed prior to navigation.
   - Verify unread counter is updated.
5. **Test Edge Cases:**
   - Verify `navigateToReference(null, null)` remains on `#notifications` without error.
   - Verify unrecognized reference type displays warning toast and stays on `#notifications`.

---

## 10. Uncertainties & Open Decisions

1. **Product Modal vs. Search:**
   - `showProductModal(productId)` opens the edit modal if the user has Manager/Owner permissions. If the user is an `Employee`, `showProductModal` can still view details or should it open in view mode? Inspection confirmed `products.js:showProductModal` handles both add and edit, but save button visibility depends on `canAdd`. This should be validated for Employee role.
2. **Quotation Notifications referencing Purchase Orders:**
   - When a quotation is submitted, `quotation_service.py` currently stores `reference_type="PurchaseOrder"` and `reference_id=po_id`.
   - When historical notifications in DB were created, they stored `reference_type="QUOTATION"` and `reference_id=quotation_id`.
   - **Resolution:** Supporting both `PurchaseOrder` (opening the PO modal, which displays the accepted terms) and `Quotation` (opening the quotation details modal) guarantees seamless navigation regardless of when or where the notification was generated.

---

## 11. Mandatory Stop Condition Confirmation

In accordance with Phase 1 instructions:
- **No source code changes have been made.**
- **No database records have been modified.**
- **No migrations have been executed.**
- **Execution is stopped here to await explicit user approval before proceeding to Phase 2.**
