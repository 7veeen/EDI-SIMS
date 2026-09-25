# Team 2: Supplier Dashboard Documentation
**Smart Inventory Management System**  
**Module:** Supplier Dashboard (Overview & Procurement Summary with Navigation Sidebar)  
**Assigned Team:** Team 2  

---

## 1. Overview
The **Supplier Dashboard** provides an enterprise light-theme interface for authenticated suppliers to track real-time procurement operations, stock requests, purchase orders, shipments, and notifications without exposing another supplier's data.

The module follows a clean separation of concerns:
- **Frontend:** Semantic HTML5, CSS3 (Light Theme), and Vanilla JavaScript (`fetch()` API communication). Includes a dedicated **Module Navigation Sidebar** listing all system features.
- **Backend:** Python + Flask with a Blueprint architecture in `backend/app/routes/team2/` and service logic in `backend/app/services/team2/`.
- **Database:** Supabase PostgreSQL with schema definitions, foreign keys, indexes, and RLS policies in `database/team2/supplier_dashboard_schema.sql`, connected via direct PostgreSQL connection pooler and Supabase client.

---

## 2. Directory & File Structure
All new Team 2 files are isolated within the designated folders:

```text
Smart Inventory Management System/
│
├── frontend/
│   └── team2/
│       ├── index.html                           # Semantic HTML5 Dashboard Structure with Sidebar
│       ├── css/
│       │   └── supplier_dashboard.css           # Clean Light-Theme Stylesheet with Sidebar & Responsive Rules
│       └── js/
│           └── supplier_dashboard.js            # Vanilla JS Controller, DOM Renderer & Sidebar Handler
│
├── backend/
│   ├── run.py                                   # Server entry point
│   └── app/
│       ├── __init__.py                          # Flask Application Factory & static routing
│       ├── config/
│       │   ├── __init__.py
│       │   ├── config.py                        # App & Supabase environment loader (DATABASE_URL, JWT_SECRET_KEY)
│       │   └── supabase_client.py               # Shared Supabase & direct PostgreSQL pooler client
│       ├── models/
│       │   ├── __init__.py
│       │   └── supplier_models.py               # Supplier data dataclasses
│       ├── routes/
│       │   └── team2/
│       │       ├── __init__.py
│       │       └── supplier_dashboard_routes.py # Flask Blueprint (/api/team2/supplier)
│       ├── services/
│       │   └── team2/
│       │       ├── __init__.py
│       │       └── supplier_dashboard_service.py# Business logic & live Supabase PostgreSQL queries
│       └── utils/
│           ├── __init__.py
│           ├── auth.py                          # Supplier auth & RBAC verification
│           └── response.py                      # Standard JSON response envelope
│
├── database/
│   └── team2/
│       └── supplier_dashboard_schema.sql        # Supabase PostgreSQL DDL migration script
│
├── tests/
│   └── team2/
│       ├── __init__.py
│       └── test_supplier_dashboard.py           # Pytest test suite (11 unit/integration tests)
│
└── documentation/
    └── team2/
        └── supplier_dashboard_documentation.md  # Comprehensive module documentation
```

---

## 3. Sidebar Features & Modules

The application layout incorporates a dedicated, responsive left sidebar navigation for all procurement features:

| Module Option | Status | Icon / Badge | Behavior |
|---|---|---|---|
| **Dashboard** | Active | Grid Icon / "Live" Badge | Displays the Supplier Dashboard overview and metrics |
| **Stock Requests** | Scope-restricted | FileText Icon | Shows toast: *"The Stock Requests module will be implemented separately as per project scope."* |
| **Quotations** | Scope-restricted | Clock / Quote Icon | Shows toast: *"The Quotations module will be implemented separately as per project scope."* |
| **Purchase Orders** | Scope-restricted | ShoppingBag Icon | Shows toast: *"The Purchase Orders module will be implemented separately as per project scope."* |
| **Shipments** | Scope-restricted | Truck Icon | Shows toast: *"The Shipments module will be implemented separately as per project scope."* |
| **Order History** | Scope-restricted | History Icon | Shows toast: *"The Order History module will be implemented separately as per project scope."* |
| **Notifications** | Active / Linked | Bell Icon / Dynamic Count Badge | Displays unread notification count badge and smoothly scrolls to notifications card |
| **Supplier Profile** | Scope-restricted | UserCheck Icon | Shows toast: *"The Supplier Profile module will be implemented separately as per project scope."* |

### Sidebar Profile Card (Bottom)
- Renders the logged-in Supplier Organization name (e.g. `Supplier 1 Company`).
- Displays the contact person (`Supplier One • Active`).
- Dynamic initials avatar badge (`S1`).

---

## 4. Supabase Database Schema & Tables Connected

The backend service directly connects to the live Supabase PostgreSQL database using the `DATABASE_URL` configured in `.env`:

| Table Name | Live Schema Columns Used | Purpose |
|---|---|---|
| `"Suppliers"` | `supplier_id`, `supplier_name`, `contact_person`, `email`, `phone`, `status`, `user_id` | Supplier identity & profile resolution |
| `"PurchaseOrders"` | `purchase_order_id`, `supplier_id`, `order_date`, `total_amount`, `status`, `expected_delivery` | Recent purchase orders & summary metrics |
| `"SupplierQuotations"` | `quotation_id`, `supplier_id`, `product_id`, `quotation_date`, `quoted_price`, `quantity`, `valid_until`, `status` | Quotations summary counts & recent stock requests |
| `"PurchaseOrderItems"` | `purchase_order_item_id`, `purchase_order_id`, `product_id`, `quantity`, `unit_price`, `subtotal` | Line item tracking |
| `"Notifications"` | `notification_id`, `user_id`, `title`, `message`, `notification_type`, `is_read`, `created_at` | Real-time supplier alerts (e.g. "Quotation Approved") |

---

## 5. API Endpoints (`/api/team2/supplier`)

All API responses follow the standard JSON envelope:
```json
{
  "success": true,
  "message": "Supplier dashboard retrieved successfully",
  "data": { ... }
}
```

1. **`GET /api/team2/supplier/dashboard`** — Returns full aggregated dashboard payload (Profile, 6 summary card counts, recent requests, POs, shipments, notifications, and database connectivity status).
2. **`GET /api/team2/supplier/summary-cards`** — Returns counts for all 6 summary cards.
3. **`GET /api/team2/supplier/recent-stock-requests?limit=5`** — Returns recent stock requests.
4. **`GET /api/team2/supplier/recent-purchase-orders?limit=5`** — Returns recent purchase orders.
5. **`GET /api/team2/supplier/pending-shipments?limit=5`** — Returns orders to ship / in-transit shipments.
6. **`GET /api/team2/supplier/notifications?limit=5`** — Returns supplier alerts and notices.
7. **`GET /api/team2/supplier/profile`** — Returns supplier organization profile.
8. **`GET /api/team2/supplier/health`** — Health check and database status.

---

## 6. Testing & Verification

### Automated Pytest Suite (`tests/team2/test_supplier_dashboard.py`)
Run with:
```bash
python -m pytest tests/team2 -v
```
**Results:** `11 passed in 26.98s`
- `test_health_check` &rarr; PASSED
- `test_dashboard_full_endpoint_authorized` &rarr; PASSED
- `test_summary_cards_endpoint` &rarr; PASSED
- `test_recent_stock_requests_endpoint` &rarr; PASSED
- `test_recent_purchase_orders_endpoint` &rarr; PASSED
- `test_pending_shipments_endpoint` &rarr; PASSED
- `test_notifications_endpoint` &rarr; PASSED
- `test_supplier_profile_endpoint` &rarr; PASSED
- `test_rbac_unauthorized_role` &rarr; PASSED
- `test_rbac_cross_supplier_tampering` &rarr; PASSED
- `test_frontend_serving` &rarr; PASSED

### Visual & Browser Verification
- Verified via browser subagent on `http://localhost:5000/`.
- Confirmed left sidebar navigation with all 8 module options.
- Confirmed `Dashboard` active state and `Supabase Live` connection badge.
- Confirmed toast alerts when clicking other modules without breaking dashboard scope.
- Confirmed live supplier profile (`Supplier 1 Company`) and live notifications (`Quotation Approved`).
