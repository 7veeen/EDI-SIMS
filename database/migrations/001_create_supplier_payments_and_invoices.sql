-- ============================================================================
-- SIMS Migration: 001_create_supplier_payments_and_invoices.sql
-- Module: Supplier Portal & Finance / Procurement Module
-- Feature: Supplier Payments MVP — Additive Schema
-- Target: Supabase PostgreSQL (public schema)
-- Date: October 11, 2026
--
-- BUSINESS RULES & ARCHITECTURAL SPECIFICATION:
-- 1. GOODS-RECEIPT ELIGIBILITY:
--    - Suppliers may submit invoices only after associated goods have been
--      delivered (Shipments.status = 'Delivered') AND goods receipt has been
--      officially recorded (Shipments.receiving_status IN ('Partially Received',
--      'Fully Received')) with corresponding StockTransactions (transaction_type =
--      'STOCK_IN', quantity > 0).
--    - Partial goods receipts are fully eligible under the confirmed MVP rules.
--    - If an invoice references a specific shipment_id, the service layer MUST
--      validate that exact shipment rather than accepting an unrelated qualifying
--      shipment on the same PO.
-- 2. REFERENTIAL CONSISTENCY:
--    - The invoice supplier MUST match the supplier on the linked Purchase Order.
--    - If shipment_id is provided, the shipment MUST belong to the same PO and supplier.
--    - Cross-table alignment with live existing tables (PurchaseOrders, Shipments)
--      is strictly enforced via backend transactional validation in Phase 2 to
--      avoid destructive ALTER TABLE DDL on existing tables.
--    - Between the new tables (SupplierPayments -> SupplierInvoices), referential
--      supplier consistency is mathematically enforced via composite FK
--      fk_payment_invoice_supplier (invoice_id, supplier_id).
-- 3. FINANCIAL CONCURRENCY & OVERPAYMENT PREVENTION:
--    - Multiple payment records may link to one invoice to support partial payments.
--    - Outstanding balance is derived: total_amount - SUM(amount_paid).
--    - Overpayment is strictly prevented via transactional row-locking in Phase 2:
--      SELECT ... FROM "SupplierInvoices" WHERE invoice_id = %s FOR UPDATE;
--    - Invoice status transitions (Submitted -> Approved -> Partially Paid -> Paid)
--      are executed atomically within the payment transaction.
--    - Financial history is immutable: zero destructive deletions or cascading drops.
-- 4. MULTIPLE INVOICES PER PO & PER-SUPPLIER UNIQUENESS:
--    - Multiple invoices may reference the same PO (split shipments / milestone billing).
--    - Invoice numbers are unique per supplier: uq_supplier_invoice_number (supplier_id, invoice_number).
--    - Different suppliers may use the same invoice number (e.g. "INV-001").
-- 5. MONETARY ACCURACY & NON-DESTRUCTIVE MIGRATION:
--    - Exact NUMERIC(12, 2) decimal precision used for all monetary amounts.
--    - Total consistency enforced: total_amount = subtotal + tax_amount.
--    - Purely additive DDL: creates verified missing objects with zero impact
--      on existing tables, columns, or live business data.
-- 6. IDEMPOTENCY & CONFLICT BEHAVIOR:
--    - The migration uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
--    - Note: IF NOT EXISTS prevents syntax failure if an object exists, but does
--      NOT verify whether a pre-existing object has the expected schema definition.
--    - If a pre-existing object with these names is detected during preflight or
--      execution, the DBA must inspect the object rather than blindly assuming
--      compatibility. No destructive drop or automatic rebuild logic is included.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Table: "SupplierInvoices"
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public."SupplierInvoices" (
    invoice_id              BIGSERIAL PRIMARY KEY,
    invoice_number          VARCHAR(100) NOT NULL,
    supplier_id             BIGINT NOT NULL,
    purchase_order_id       BIGINT NOT NULL,
    shipment_id             BIGINT NULL,
    invoice_date            DATE NOT NULL,
    due_date                DATE NOT NULL,
    subtotal                NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount              NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_amount            NUMERIC(12, 2) NOT NULL,
    status                  VARCHAR(30) NOT NULL DEFAULT 'Submitted',
    rejection_reason        TEXT NULL,
    notes                   TEXT NULL,
    created_by              BIGINT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Foreign Key Constraints (Protecting financial integrity with RESTRICT)
    CONSTRAINT fk_invoice_supplier 
        FOREIGN KEY (supplier_id) 
        REFERENCES public."Suppliers"(supplier_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    CONSTRAINT fk_invoice_purchase_order 
        FOREIGN KEY (purchase_order_id) 
        REFERENCES public."PurchaseOrders"(purchase_order_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    CONSTRAINT fk_invoice_shipment 
        FOREIGN KEY (shipment_id) 
        REFERENCES public."Shipments"(shipment_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    CONSTRAINT fk_invoice_created_by 
        FOREIGN KEY (created_by) 
        REFERENCES public."Users"(user_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    -- Uniqueness Constraints:
    -- A supplier cannot submit the same invoice number more than once.
    -- Multiple suppliers MAY use the same invoice number (e.g., "INV-001").
    -- Multiple invoices MAY reference the same Purchase Order.
    CONSTRAINT uq_supplier_invoice_number 
        UNIQUE (supplier_id, invoice_number),

    -- Composite unique key to support composite FK in SupplierPayments
    CONSTRAINT uq_supplier_invoice_composite 
        UNIQUE (invoice_id, supplier_id),

    -- Integrity & Domain Check Constraints
    CONSTRAINT chk_invoice_due_date 
        CHECK (due_date >= invoice_date),

    CONSTRAINT chk_invoice_subtotal 
        CHECK (subtotal >= 0.00),

    CONSTRAINT chk_invoice_tax 
        CHECK (tax_amount >= 0.00),

    CONSTRAINT chk_invoice_total_positive 
        CHECK (total_amount > 0.00),

    CONSTRAINT chk_invoice_total_consistency 
        CHECK (total_amount = subtotal + tax_amount),

    CONSTRAINT chk_invoice_status 
        CHECK (status IN ('Submitted', 'Approved', 'Rejected', 'Partially Paid', 'Paid', 'Cancelled'))
);

-- Comments on "SupplierInvoices"
COMMENT ON TABLE public."SupplierInvoices" IS 
    'Stores supplier invoices issued against delivered and received purchase orders in SIMS.';
COMMENT ON COLUMN public."SupplierInvoices".invoice_id IS 
    'Primary key for the supplier invoice.';
COMMENT ON COLUMN public."SupplierInvoices".invoice_number IS 
    'Supplier-assigned invoice or bill reference number. Unique per supplier.';
COMMENT ON COLUMN public."SupplierInvoices".purchase_order_id IS 
    'Reference to the associated purchase order. Multiple invoices may reference one PO.';
COMMENT ON COLUMN public."SupplierInvoices".shipment_id IS 
    'Optional reference to a specific delivered shipment linked to this invoice.';
COMMENT ON COLUMN public."SupplierInvoices".total_amount IS 
    'Total payable amount in INR. Enforced to equal subtotal + tax_amount.';
COMMENT ON COLUMN public."SupplierInvoices".status IS 
    'Invoice workflow status: Submitted, Approved, Rejected, Partially Paid, Paid, Cancelled.';


-- Indexes on "SupplierInvoices" for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_invoices_supplier 
    ON public."SupplierInvoices"(supplier_id);

CREATE INDEX IF NOT EXISTS idx_invoices_po 
    ON public."SupplierInvoices"(purchase_order_id);

CREATE INDEX IF NOT EXISTS idx_invoices_shipment 
    ON public."SupplierInvoices"(shipment_id);

CREATE INDEX IF NOT EXISTS idx_invoices_status 
    ON public."SupplierInvoices"(status);

CREATE INDEX IF NOT EXISTS idx_invoices_due_date 
    ON public."SupplierInvoices"(due_date);

CREATE INDEX IF NOT EXISTS idx_invoices_created_at 
    ON public."SupplierInvoices"(created_at DESC);


-- ----------------------------------------------------------------------------
-- 2. Table: "SupplierPayments"
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public."SupplierPayments" (
    payment_id              BIGSERIAL PRIMARY KEY,
    invoice_id              BIGINT NOT NULL,
    supplier_id             BIGINT NOT NULL,
    payment_date            DATE NOT NULL,
    amount_paid             NUMERIC(12, 2) NOT NULL,
    payment_method          VARCHAR(50) NOT NULL,
    payment_reference       VARCHAR(100) NOT NULL,
    notes                   TEXT NULL,
    recorded_by             BIGINT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Composite Foreign Key: Mathematically guarantees that a payment's
    -- supplier_id strictly matches the invoice's supplier_id.
    CONSTRAINT fk_payment_invoice_supplier 
        FOREIGN KEY (invoice_id, supplier_id) 
        REFERENCES public."SupplierInvoices"(invoice_id, supplier_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    -- Redundant standalone FK for supplier table query plan optimization
    CONSTRAINT fk_payment_supplier 
        FOREIGN KEY (supplier_id) 
        REFERENCES public."Suppliers"(supplier_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    -- Foreign Key: User who recorded the disbursement
    CONSTRAINT fk_payment_recorded_by 
        FOREIGN KEY (recorded_by) 
        REFERENCES public."Users"(user_id) 
        ON DELETE RESTRICT 
        ON UPDATE NO ACTION,

    -- Integrity & Domain Check Constraints
    CONSTRAINT chk_payment_amount 
        CHECK (amount_paid > 0.00),

    CONSTRAINT chk_payment_method 
        CHECK (payment_method IN (
            'Bank Transfer / NEFT',
            'RTGS',
            'Cheque',
            'UPI',
            'Wire Transfer',
            'Cash',
            'Other'
        ))
);

-- Comments on "SupplierPayments"
COMMENT ON TABLE public."SupplierPayments" IS 
    'Stores accounts payable disbursements and payment transactions recorded against approved supplier invoices.';
COMMENT ON COLUMN public."SupplierPayments".payment_id IS 
    'Primary key for the payment record.';
COMMENT ON COLUMN public."SupplierPayments".invoice_id IS 
    'Reference to the invoice being paid. Supports multiple partial payments per invoice.';
COMMENT ON COLUMN public."SupplierPayments".supplier_id IS 
    'Supplier receiving the payment, strictly bound to invoice.supplier_id via composite FK.';
COMMENT ON COLUMN public."SupplierPayments".amount_paid IS 
    'Monetary amount disbursed in INR. Overpayment is prevented by service-layer transactional locks.';
COMMENT ON COLUMN public."SupplierPayments".payment_reference IS 
    'Internal or bank reference (UTR number, cheque number, or bank transaction identifier).';
COMMENT ON COLUMN public."SupplierPayments".payment_method IS 
    'Corporate payment disbursement method.';


-- Indexes on "SupplierPayments" for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_payments_invoice 
    ON public."SupplierPayments"(invoice_id);

CREATE INDEX IF NOT EXISTS idx_payments_supplier 
    ON public."SupplierPayments"(supplier_id);

CREATE INDEX IF NOT EXISTS idx_payments_date 
    ON public."SupplierPayments"(payment_date DESC);

CREATE INDEX IF NOT EXISTS idx_payments_reference 
    ON public."SupplierPayments"(payment_reference);

CREATE INDEX IF NOT EXISTS idx_payments_created_at 
    ON public."SupplierPayments"(created_at DESC);

COMMIT;
