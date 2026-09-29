# SIMS Team 2 — Shipment & History Module Documentation

**Module Owner:** Soumya  
**Branch:** `team2`  
**Framework:** Flask (Python) + Vanilla JS + Supabase PostgreSQL

---

## 1. Module Overview

The **Shipment & History** module handles the complete fulfillment lifecycle for a logged-in supplier:

| Feature | Endpoint |
|---|---|
| Mark order ready for shipment | `POST /api/team2/supplier/shipments/ready` |
| Enter shipment details (carrier, tracking, etc.) | `POST /api/team2/supplier/shipments/details` |
| Update shipment status (in transit, delayed, etc.) | `PUT /api/team2/supplier/shipments/<id>/status` |
| Mark shipped (dispatch confirmation) | `POST /api/team2/supplier/shipments/<id>/mark-shipped` |
| Update expected delivery date | `PUT /api/team2/supplier/shipments/<id>/expected-delivery` |
| Mark delivered | `POST /api/team2/supplier/shipments/<id>/mark-delivered` |
| List all active shipments | `GET /api/team2/supplier/shipments` |
| List completed (delivered) shipments | `GET /api/team2/supplier/shipments/completed` |
| View shipment detail + timeline | `GET /api/team2/supplier/shipments/<id>` |
| Fulfillment stats | `GET /api/team2/supplier/shipments/stats` |
| Previous purchase orders | `GET /api/team2/supplier/history/purchase-orders` |
| Previous quotations | `GET /api/team2/supplier/history/quotations` |
| Order status history timeline | `GET /api/team2/supplier/history/all` |
| Order history for specific PO | `GET /api/team2/supplier/history/order/<po_id>` |

---

## 2. Files Created

### Backend
| File | Purpose |
|---|---|
| `backend/app/services/team2/supplier_shipment_service.py` | All business logic for shipments & history |
| `backend/app/routes/team2/supplier_shipment_routes.py` | All API route definitions (Blueprint) |

### Frontend
| File | Purpose |
|---|---|
| `frontend/team2/shipments.html` | Shipments & Fulfillment page |
| `frontend/team2/order-history.html` | Previous POs, Quotations, History Timeline |
| `frontend/team2/js/shipments.js` | Shipments controller |
| `frontend/team2/js/order-history.js` | History controller |
| `frontend/team2/css/shipments.css` | Shared CSS for both pages |

### Database
| File | Purpose |
|---|---|
| `database/team2/create_shipments_and_history_tables.sql` | Creates `Shipments` and `OrderStatusHistory` tables + seed data |
| `database/team2/seed_supplier_quotations.sql` | Seeds sample `SupplierQuotations` data |

### Tests
| File | Purpose |
|---|---|
| `tests/team2/test_supplier_shipment.py` | 13 integration + RBAC tests |

### Shared Files Modified
| File | Change |
|---|---|
| `backend/app/__init__.py` | Register `supplier_shipment_bp`, add frontend route serving |
| `backend/app/routes/team2/__init__.py` | Export `supplier_shipment_bp` |
| `backend/app/services/team2/__init__.py` | Export `SupplierShipmentService` |
| `backend/app/models/supplier_models.py` | Add `Shipment`, `OrderStatusHistoryEntry`, `QuotationHistoryItem` dataclasses |
| `backend/app/services/team2/supplier_dashboard_service.py` | Update `get_pending_shipments` to query `Shipments` table |
| `frontend/team2/index.html` | Wire Shipments and Order History nav links |

---

## 3. Database Schema

### `Shipments` Table
```sql
CREATE TABLE "Shipments" (
    shipment_id       BIGSERIAL PRIMARY KEY,
    shipment_number   VARCHAR(100) UNIQUE NOT NULL,
    purchase_order_id BIGINT NOT NULL REFERENCES "PurchaseOrders",
    supplier_id       BIGINT NOT NULL REFERENCES "Suppliers",
    carrier           VARCHAR(100) NOT NULL DEFAULT 'Standard Logistics',
    tracking_number   VARCHAR(150),
    shipping_method   VARCHAR(100) DEFAULT 'Standard Ground',
    status            VARCHAR(50) NOT NULL DEFAULT 'Ready for Shipment',
    package_count     INTEGER DEFAULT 1,
    total_weight      NUMERIC(10,2),
    shipping_notes    TEXT,
    origin_address    TEXT,
    destination_address TEXT,
    expected_delivery DATE,
    shipped_at        TIMESTAMPTZ,
    delivered_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
```

**Valid statuses:** `Ready for Shipment`, `Shipped`, `In Transit`, `Out for Delivery`, `Delivered`, `Delayed`, `Cancelled`

### `OrderStatusHistory` Table
```sql
CREATE TABLE "OrderStatusHistory" (
    history_id        BIGSERIAL PRIMARY KEY,
    purchase_order_id BIGINT NOT NULL REFERENCES "PurchaseOrders",
    shipment_id       BIGINT REFERENCES "Shipments",
    supplier_id       BIGINT NOT NULL REFERENCES "Suppliers",
    status            VARCHAR(50) NOT NULL,
    previous_status   VARCHAR(50),
    action            VARCHAR(100) NOT NULL,
    location          VARCHAR(255),
    notes             TEXT,
    changed_by        VARCHAR(100) DEFAULT 'Supplier',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. API Reference

### GET /api/team2/supplier/shipments
Returns all shipments for the authenticated supplier.  
**Query params:** `status`, `search`  
**Headers:** `X-Supplier-Id`, `X-User-Role: supplier`

### POST /api/team2/supplier/shipments/ready
Mark an accepted PO ready for shipment.  
**Body:** `{ "purchase_order_id": 4, "notes": "..." }`

### POST /api/team2/supplier/shipments/details
Enter carrier, tracking, package count, weight, delivery date.  
**Body:** `{ "purchase_order_id": 4, "carrier": "BlueDart", "tracking_number": "BD-...", ... }`

### POST /api/team2/supplier/shipments/<id>/mark-shipped
Marks shipment as dispatched.  
**Body:** `{ "carrier": "FedEx", "tracking_number": "...", "expected_delivery": "2026-10-05" }`

### PUT /api/team2/supplier/shipments/<id>/status
Updates status (In Transit, Out for Delivery, Delayed, etc.).  
**Body:** `{ "status": "In Transit", "location": "Mumbai Hub", "notes": "..." }`

### PUT /api/team2/supplier/shipments/<id>/expected-delivery
Revises expected delivery date.  
**Body:** `{ "expected_delivery": "2026-10-06", "reason": "..." }`

### POST /api/team2/supplier/shipments/<id>/mark-delivered
Confirms delivery.  
**Body:** `{ "notes": "Signed by receiving officer" }`

### GET /api/team2/supplier/history/purchase-orders
All previous purchase orders. **Query params:** `status`, `search`

### GET /api/team2/supplier/history/quotations
All previous quotations. **Query params:** `status`, `search`

### GET /api/team2/supplier/history/all
Full status lifecycle audit trail. **Query params:** `purchase_order_id`, `shipment_id`

---

## 5. Authentication & RBAC

- All endpoints use the existing `@require_supplier_auth` decorator from `backend/app/utils/auth.py`
- `X-Supplier-Id` and `X-User-Role: supplier` headers required
- Supplier data isolation enforced: every query filters by `supplier_id`  
- Cross-supplier access returns `403 Forbidden`  
- Missing shipments return `404 Not Found`

---

## 6. Frontend Pages

### shipments.html
- **Stats bar:** Ready to Ship, In Transit, Delivered, Total POs, Quotations, On-Time Rate
- **Tabs:** Active Shipments | Ready to Ship | Completed
- **Actions per shipment:** View Details, Update Status, Mark Shipped, Mark Delivered
- **Modals:** Shipment Detail with timeline, Enter Details Form, Status Update, Mark Shipped

### order-history.html
- **Tab 1 — Previous Purchase Orders:** Full table with status, items, shipment info, "View Timeline" action
- **Tab 2 — Previous Quotations:** Product, SKU, category, price, qty, valid until, status
- **Tab 3 — Order/Status History:** Chronological timeline with PO filter, location, changed_by

---

## 7. Cross-Team Integration

- **Reuses:** `PurchaseOrders`, `Suppliers`, `Users`, `Products`, `Categories`, `SupplierQuotations`, `PurchaseOrderItems` tables from shared schema
- **Adds:** `Shipments` (new), `OrderStatusHistory` (new)
- **Dashboard integration:** `get_pending_shipments()` in `supplier_dashboard_service.py` was updated to first query the `Shipments` table and fall back to `PurchaseOrders`
- **No other team files modified**

---

## 8. Testing

All tests in `tests/team2/test_supplier_shipment.py`:

| Test | Covers |
|---|---|
| `test_get_shipments_list` | Active shipments listing |
| `test_get_orders_ready_to_ship` | Orders ready for dispatch |
| `test_get_completed_shipments` | Delivered shipments |
| `test_get_fulfillment_stats` | Summary stats |
| `test_mark_order_ready_for_shipment` | Mark ready action |
| `test_enter_shipment_details` | Carrier/tracking entry |
| `test_update_expected_delivery` | Delivery date revision |
| `test_update_shipment_status_and_mark_shipped` | Shipped + In Transit flow |
| `test_mark_as_delivered` | Delivery confirmation |
| `test_previous_purchase_orders` | History POs |
| `test_previous_quotations` | Previous quotations |
| `test_order_status_history_timeline` | Timeline events |
| `test_rbac_supplier_isolation` | Cross-supplier RBAC |
