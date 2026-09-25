-- ====================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2 (SUPPLIER DASHBOARD SCHEMA)
-- Shared Supabase PostgreSQL Schema Definition & Setup Script
-- ====================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. SUPPLIERS TABLE
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    category VARCHAR(100) DEFAULT 'General Supplies',
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    rating NUMERIC(3, 2) DEFAULT 5.00 CHECK (rating >= 0.0 AND rating <= 5.0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. STOCK REQUESTS TABLE
CREATE TABLE IF NOT EXISTS stock_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    items_summary TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    department VARCHAR(100) DEFAULT 'Central Warehouse',
    urgency VARCHAR(50) DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high', 'critical')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'approved', 'rejected', 'fulfilled')),
    request_date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. QUOTATIONS TABLE
CREATE TABLE IF NOT EXISTS quotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quotation_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    request_id UUID REFERENCES stock_requests(id) ON DELETE SET NULL,
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'under_review', 'accepted', 'rejected', 'expired')),
    valid_until TIMESTAMPTZ,
    submission_date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. PURCHASE ORDERS TABLE
CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    quotation_id UUID REFERENCES quotations(id) ON DELETE SET NULL,
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    payment_terms VARCHAR(100) DEFAULT 'Net 30',
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled')),
    order_date TIMESTAMPTZ DEFAULT NOW(),
    delivery_deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. PURCHASE ORDER ITEMS TABLE
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    total_price NUMERIC(12, 2) NOT NULL CHECK (total_price >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. SHIPMENTS TABLE
CREATE TABLE IF NOT EXISTS shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_number VARCHAR(100) UNIQUE NOT NULL,
    po_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    carrier VARCHAR(100),
    tracking_number VARCHAR(150),
    status VARCHAR(50) DEFAULT 'orders_to_ship' CHECK (status IN ('orders_to_ship', 'shipped', 'in_transit', 'delivered', 'cancelled')),
    shipped_at TIMESTAMPTZ,
    expected_delivery TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    shipping_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. NOTIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info' CHECK (type IN ('info', 'order', 'request', 'quotation', 'shipment', 'alert')),
    is_read BOOLEAN DEFAULT FALSE,
    link_url VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_stock_requests_supplier_status ON stock_requests(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_stock_requests_request_date ON stock_requests(request_date DESC);

CREATE INDEX IF NOT EXISTS idx_quotations_supplier_status ON quotations(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_quotations_submission_date ON quotations(submission_date DESC);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_status ON purchase_orders(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_order_date ON purchase_orders(order_date DESC);

CREATE INDEX IF NOT EXISTS idx_shipments_supplier_status ON shipments(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_shipments_expected_delivery ON shipments(expected_delivery ASC);

CREATE INDEX IF NOT EXISTS idx_notifications_supplier_unread ON notifications(supplier_id, is_read, created_at DESC);

-- 10. ROW LEVEL SECURITY (RLS) POLICIES FOR SUPABASE
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Note: In Supabase, RLS policies ensure suppliers can only view their own records.
-- Example policy:
-- CREATE POLICY "Suppliers can view only their own records"
-- ON stock_requests FOR SELECT
-- USING (auth.uid() = supplier_id);
