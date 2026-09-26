# Team 2: Supplier Purchase Order Module Documentation
**Smart Inventory Management System**  
**Module:** Supplier Purchase Order Section  
**Assigned Team:** Team 2  

---

## 1. Overview
The **Supplier Purchase Order Module** allows authenticated suppliers to view, inspect, accept, and reject Purchase Orders issued to their organization by Inventory Managers and Owners.

### Scope Boundaries Strictly Enforced:
- **Supplier-Side Only:** Suppliers cannot create, edit quantities, or delete original Purchase Orders.
- **Read-Only Pricing & Quantities:** The original PO total and line item quantities are fixed by the manager and strictly non-editable.
- **Scope Restriction:** Quotations, Shipments, Invoices, Delivery, and Products are separate modules and are not implemented in this task.

---

## 2. File Structure

```text
Smart Inventory Management System/
│
├── frontend/team2/
│   ├── purchase-orders.html               # Semantic HTML5 PO page with modal dialogs
│   ├── purchase-orders.css                # Root reference CSS
│   ├── purchase-orders.js                 # Root reference JS
│   ├── css/
│   │   └── purchase-orders.css            # Modular Light Theme styles for PO section
│   └── js/
│       └── purchase-orders.js             # Vanilla JS controller for PO workflows
│
├── backend/app/
│   ├── routes/team2/
│   │   ├── __init__.py                    # Blueprint exports
│   │   └── supplier_po_routes.py          # Flask Blueprint for PO endpoints
│   └── services/team2/
│       ├── __init__.py                    # Service exports
│       └── supplier_po_service.py         # Business logic, Supabase SQL & RBAC
│
├── database/team2/
│   ├── add_supplier_po_response_fields.sql# Non-destructive migration script
│   └── seed_sample_purchase_orders.sql    # Real database test records
│
├── tests/team2/
│   └── test_supplier_purchase_orders.py   # Pytest suite (8 unit & integration tests)
│
└── documentation/team2/
    └── supplier_po_documentation.md       # Comprehensive module documentation
```

---

## 3. Database Schema & Changes

### 3.1 Existing Tables Used
- `"PurchaseOrders"` — Stores purchase order headers (`purchase_order_id`, `supplier_id`, `ordered_by`, `order_date`, `expected_delivery`, `total_amount`, `status`).
- `"PurchaseOrderItems"` — Stores line items (`purchase_order_item_id`, `purchase_order_id`, `product_id`, `quantity`, `unit_price`, `subtotal`).
- `"Products"` — Product catalog (`product_id`, `product_name`, `sku`, `category_id`, `selling_price`).
- `"Categories"` — Product category lookup (`category_id`, `category_name`).
- `"Suppliers"` — Supplier profile (`supplier_id`, `supplier_name`, `contact_person`, `email`, `phone`, `status`, `user_id`).
- `"Users"` — Requesting manager details (`user_id`, `username`, `email`, `role_id`).

### 3.2 Database Changes Made (`database/team2/add_supplier_po_response_fields.sql`)
To support the supplier acceptance/rejection response workflow without destroying or altering existing columns:

| Table | Column Added | Data Type | Purpose |
|---|---|---|---|
| `"PurchaseOrders"` | `supplier_response` | `VARCHAR(50) DEFAULT 'Pending'` | Stores the supplier's explicit response state (`Pending`, `Accepted`, `Rejected`) |
| `"PurchaseOrders"` | `supplier_response_date` | `TIMESTAMPTZ` | Timestamp when the supplier accepted or rejected the PO |
| `"PurchaseOrders"` | `rejection_reason` | `TEXT` | Optional explanation provided by the supplier when declining an order |

### 3.3 Indexes Added
- `idx_purchase_orders_supplier_response` on `"PurchaseOrders"(supplier_id, supplier_response)` for query performance when filtering by supplier and status.

### 3.4 Reason for Database Changes
The existing `"PurchaseOrders"` table contained only a general `status` column without fields to record distinct supplier responses, response timestamps, or rejection rationales. The additions are non-destructive and maintain full backward compatibility with Manager-side PO workflows.

---

## 4. API Endpoints

Base Route: `/api/team2/supplier/purchase-orders`  
Authorization: `@require_supplier_auth` (Requires role `supplier` or `admin`, verifies `X-Supplier-Id`)

### 4.1 `GET /api/team2/supplier/purchase-orders`
- **Query Parameters:**
  - `status`: Optional filter (`Pending`, `Accepted`, `Rejected`, `all`).
  - `search`: Search string matched against PO ID or product name.
- **Response:** List of purchase orders assigned to the logged-in supplier.

### 4.2 `GET /api/team2/supplier/purchase-orders/<int:po_id>`
- **Description:** Returns complete details of a specific PO including:
  - Header: PO ID, dates, total amount, manager info, supplier response, rejection reason.
  - Items: List of line items with product name, SKU, category, quantity, unit price, and subtotal.
- **RBAC:** Rejects unauthorized cross-supplier access with `403 Forbidden`.

### 4.3 `POST /api/team2/supplier/purchase-orders/<int:po_id>/accept`
- **Description:** Accepts a pending purchase order.
- **State Transition:** Validates current response is `Pending`. Updates `supplier_response = 'Accepted'`, `status = 'Accepted'`, and `supplier_response_date = NOW()`.
- **Validation:** Disallows accepting already accepted or rejected POs with `400 Bad Request`.

### 4.4 `POST /api/team2/supplier/purchase-orders/<int:po_id>/reject`
- **Body:** `{"reason": "..."}`
- **Description:** Declines a pending purchase order with optional reason.
- **State Transition:** Updates `supplier_response = 'Rejected'`, `status = 'Rejected'`, `rejection_reason = reason`, and `supplier_response_date = NOW()`.

### 4.5 `GET /api/team2/supplier/purchase-orders/suppliers`
- **Description:** Returns all registered suppliers from the database for dynamic account switching.

### 4.6 `GET /api/team2/supplier/purchase-orders/current-supplier`
- **Description:** Returns the authenticated supplier's company profile, contact person, and status.

---

## 5. Supplier Data Isolation & Dynamic Resolution

### 5.1 Dynamic Supplier Authentication
- The frontend dynamically determines the logged-in supplier using:
  1. URL search parameter: `?supplier_id=<id>`
  2. `localStorage` active supplier item (`sims_active_supplier_id` / `supplier_id`)
  3. Stored user object from authentication module
  4. Database default fallback
- In the top header bar, a dynamic **Supplier Account Selector** allows switching between registered suppliers (`Supplier 1 Company (ID: 4)` vs `Demo Supplier Company (ID: 5)`).
- When switched, the state immediately updates `localStorage`, synchronizes the URL query parameter, and reloads the PO table strictly for that supplier.

### 5.2 Strict Backend Data Isolation
- `SupplierPurchaseOrderService._resolve_supplier_id()` resolves the incoming identifier (integer, string, or `user_id`) to the exact primary key in the `"Suppliers"` table.
- All SQL queries use `WHERE po.supplier_id = %s` parameterized strictly with the resolved supplier ID.
- No cross-supplier leakage: POs assigned to Supplier 4 are never visible to Supplier 5 and vice-versa.
- Attempting to inspect or respond to a PO belonging to another supplier triggers an immediate `403 Forbidden` response.

---

## 6. Frontend Features & User Interface

### 6.1 Clean Light Theme
- White cards (`#FFFFFF`), light canvas (`#F8FAFC`), subtle slate borders (`#E2E8F0`), and dark typography (`#0F172A`).
- Status badges:
  - `Pending`: Amber / Yellow badge
  - `Accepted`: Emerald Green badge
  - `Rejected`: Rose Red badge

### 6.2 PO Listing & Filtering
- Professional table listing assigned purchase orders:
  - Columns: `PO ID`, `Order Date`, `Category`, `Items`, `Original PO Total`, `PO Status`, `Supplier Response`, `Action`.
  - Search input for real-time filtering by ID or product.
  - Status dropdown filter.

### 6.3 PO Details Modal
- Header displaying PO Number and status badges.
- Metadata Grid: Order Date, Delivery Deadline, Requesting Manager, Supplier Org.
- Highlight Box: **Original PO Total** (read-only, fixed by manager).
- Line Items Table: Product Name, SKU, Category, Required Quantity, Unit Price, Subtotal.
- Action Buttons:
  - `[ Accept PO ]` &rarr; Opens Confirmation Modal.
  - `[ Reject PO ]` &rarr; Opens Decline Modal with Reason textarea.
  - If already responded: Disables actions and displays status notice with response date.

---

## 7. Testing & Results

### Automated Pytest Suite (`tests/team2/test_supplier_purchase_orders.py`)
Run via:
```bash
python -m pytest tests/team2 -v
```

**Results (22 passed out of 22 tests):**
1. `test_get_purchase_orders_list` &rarr; PASSED
2. `test_search_and_filter_po` &rarr; PASSED
3. `test_get_purchase_order_details` &rarr; PASSED
4. `test_accept_purchase_order` &rarr; PASSED
5. `test_reject_purchase_order` &rarr; PASSED
6. `test_unauthorized_po_access` &rarr; PASSED (403 Forbidden verified)
7. `test_po_not_found` &rarr; PASSED (404 Not Found verified)
8. `test_frontend_serving` &rarr; PASSED (Serves HTML, CSS, JS)
9. `test_supplier_specific_data_isolation` &rarr; PASSED (Multi-supplier isolation verified)
10. `test_get_suppliers_list` &rarr; PASSED (Dynamic suppliers list verified)
11. `test_current_supplier_profile` &rarr; PASSED (Authenticated profile verified)
12. All 11 Supplier Dashboard tests &rarr; PASSED
