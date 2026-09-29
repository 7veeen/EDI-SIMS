-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
-- Module: Soumya — Shipment & History
-- Schema Migration: Create Shipments and OrderStatusHistory Tables
-- Target: Supabase Shared PostgreSQL Database
-- ====================================================================

-- 1. SHIPMENTS TABLE
CREATE TABLE IF NOT EXISTS "Shipments" (
    shipment_id BIGSERIAL PRIMARY KEY,
    shipment_number VARCHAR(100) UNIQUE NOT NULL,
    purchase_order_id BIGINT NOT NULL REFERENCES "PurchaseOrders"(purchase_order_id) ON DELETE CASCADE,
    supplier_id BIGINT NOT NULL REFERENCES "Suppliers"(supplier_id) ON DELETE CASCADE,
    carrier VARCHAR(100) NOT NULL DEFAULT 'Standard Logistics',
    tracking_number VARCHAR(150),
    shipping_method VARCHAR(100) DEFAULT 'Standard Ground',
    status VARCHAR(50) NOT NULL DEFAULT 'Ready for Shipment',
    package_count INTEGER DEFAULT 1 CHECK (package_count > 0),
    total_weight NUMERIC(10, 2),
    shipping_notes TEXT,
    origin_address TEXT,
    destination_address TEXT,
    expected_delivery DATE,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. ORDER & SHIPMENT STATUS HISTORY (AUDIT TRAIL)
CREATE TABLE IF NOT EXISTS "OrderStatusHistory" (
    history_id BIGSERIAL PRIMARY KEY,
    purchase_order_id BIGINT NOT NULL REFERENCES "PurchaseOrders"(purchase_order_id) ON DELETE CASCADE,
    shipment_id BIGINT REFERENCES "Shipments"(shipment_id) ON DELETE CASCADE,
    supplier_id BIGINT NOT NULL REFERENCES "Suppliers"(supplier_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    previous_status VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    notes TEXT,
    changed_by VARCHAR(100) DEFAULT 'Supplier',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_shipments_supplier_status 
    ON "Shipments"(supplier_id, status);

CREATE INDEX IF NOT EXISTS idx_shipments_po_id 
    ON "Shipments"(purchase_order_id);

CREATE INDEX IF NOT EXISTS idx_shipments_expected_delivery 
    ON "Shipments"(expected_delivery ASC);

CREATE INDEX IF NOT EXISTS idx_order_status_history_po 
    ON "OrderStatusHistory"(purchase_order_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_status_history_shipment 
    ON "OrderStatusHistory"(shipment_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_status_history_supplier 
    ON "OrderStatusHistory"(supplier_id);

-- 4. SEED INITIAL SHIPMENTS FOR ACCEPTED PURCHASE ORDERS
-- Purchase Order 4 (Supplier 4)
INSERT INTO "Shipments" (
    shipment_number, purchase_order_id, supplier_id, carrier, 
    tracking_number, shipping_method, status, package_count, 
    total_weight, shipping_notes, expected_delivery, shipped_at, created_at
)
SELECT 
    'SHP-PO04-001', 4, 4, 'BlueDart Express', 
    'BD-789214582', 'Express Air', 'In Transit', 3, 
    14.50, 'Fragile electronic components packaged with protective cushioning.', 
    CURRENT_DATE + INTERVAL '2 days', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'
WHERE EXISTS (SELECT 1 FROM "PurchaseOrders" WHERE purchase_order_id = 4)
  AND NOT EXISTS (SELECT 1 FROM "Shipments" WHERE shipment_number = 'SHP-PO04-001');

-- History for PO 4
INSERT INTO "OrderStatusHistory" (purchase_order_id, shipment_id, supplier_id, status, previous_status, action, location, notes, changed_by, created_at)
SELECT 
    4, s.shipment_id, 4, 'Accepted', 'Pending', 'Order Accepted', 'Supplier HQ', 'Order accepted by supplier and scheduled for fulfillment', 'Supplier 1 Company', NOW() - INTERVAL '2 days'
FROM "Shipments" s WHERE s.shipment_number = 'SHP-PO04-001'
  AND NOT EXISTS (SELECT 1 FROM "OrderStatusHistory" WHERE purchase_order_id = 4 AND action = 'Order Accepted');

INSERT INTO "OrderStatusHistory" (purchase_order_id, shipment_id, supplier_id, status, previous_status, action, location, notes, changed_by, created_at)
SELECT 
    4, s.shipment_id, 4, 'Ready for Shipment', 'Accepted', 'Marked Ready for Shipment', 'Central Warehouse Dock', 'Goods packed, labeled, and staged for courier pickup', 'Supplier 1 Company', NOW() - INTERVAL '1 day' - INTERVAL '4 hours'
FROM "Shipments" s WHERE s.shipment_number = 'SHP-PO04-001'
  AND NOT EXISTS (SELECT 1 FROM "OrderStatusHistory" WHERE purchase_order_id = 4 AND action = 'Marked Ready for Shipment');

INSERT INTO "OrderStatusHistory" (purchase_order_id, shipment_id, supplier_id, status, previous_status, action, location, notes, changed_by, created_at)
SELECT 
    4, s.shipment_id, 4, 'In Transit', 'Ready for Shipment', 'Dispatched / In Transit', 'Mumbai Logistics Hub', 'Package scanned and in transit with BlueDart Express (BD-789214582)', 'BlueDart Courier', NOW() - INTERVAL '1 day'
FROM "Shipments" s WHERE s.shipment_number = 'SHP-PO04-001'
  AND NOT EXISTS (SELECT 1 FROM "OrderStatusHistory" WHERE purchase_order_id = 4 AND action = 'Dispatched / In Transit');

-- Purchase Order 8 (Supplier 5)
INSERT INTO "Shipments" (
    shipment_number, purchase_order_id, supplier_id, carrier, 
    tracking_number, shipping_method, status, package_count, 
    total_weight, shipping_notes, expected_delivery, shipped_at, delivered_at, created_at
)
SELECT 
    'SHP-PO08-001', 8, 5, 'FedEx Ground', 
    'FX-990145821', 'Standard Ground', 'Delivered', 2, 
    8.20, 'Delivered directly to Receiving Bay 2.', 
    CURRENT_DATE - INTERVAL '1 day', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day', NOW() - INTERVAL '3 days'
WHERE EXISTS (SELECT 1 FROM "PurchaseOrders" WHERE purchase_order_id = 8)
  AND NOT EXISTS (SELECT 1 FROM "Shipments" WHERE shipment_number = 'SHP-PO08-001');

-- History for PO 8
INSERT INTO "OrderStatusHistory" (purchase_order_id, shipment_id, supplier_id, status, previous_status, action, location, notes, changed_by, created_at)
SELECT 
    8, s.shipment_id, 5, 'Delivered', 'In Transit', 'Marked Delivered', 'Receiving Bay 2', 'Shipment successfully delivered and signed by warehouse receiver', 'FedEx Driver', NOW() - INTERVAL '1 day'
FROM "Shipments" s WHERE s.shipment_number = 'SHP-PO08-001'
  AND NOT EXISTS (SELECT 1 FROM "OrderStatusHistory" WHERE purchase_order_id = 8 AND action = 'Marked Delivered');
