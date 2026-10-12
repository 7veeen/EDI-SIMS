# SIMS Supplier Payments MVP — Phase 1: Schema Inspection, Migration Preparation & Preflight Report

**Date:** October 11, 2026  
**Module:** Supplier Portal & Finance / Procurement Module  
**Feature:** Supplier Invoices & Payment Tracking (MVP)  
**Phase:** Phase 1 — Schema Inspection, Design, Migration Preparation & Preflight  
**Status:** Completed & Preflight Verified (Ready for DBA Approval; Live DDL Execution Deferred to Phase 2)  

---

## 1. Existing Schema Findings

A thorough, read-only architectural inspection of the live Supabase PostgreSQL database was conducted via `information_schema.tables`, `information_schema.columns`, `information_schema.table_constraints`, and `pg_indexes`.

### 1.1 Verified Facts (Directly Inspected)
1. **Absence of Invoice and Payment Tables:**
   - Neither `public."Invoices"`, `public."Payments"`, `public."SupplierInvoices"`, nor `public."SupplierPayments"` exists in the live database.
   - None of the 19 existing tables contains columns for invoice numbers, due dates, payment status, paid amounts, payment references, or outstanding balances.
2. **Table Naming & Quoted Identifiers:**
   - All tables in SIMS follow PascalCase naming and require quoted identifiers in PostgreSQL:  
     `"Users"`, `"Roles"`, `"Suppliers"`, `"PurchaseOrders"`, `"PurchaseOrderItems"`, `"SupplierQuotations"`, `"Shipments"`, `"StockRequests"`, `"StockRequestItems"`, `"StockTransactions"`, `"OrderStatusHistory"`, `"AuditLogs"`.
3. **Primary Key Conventions:**
   - Every existing entity uses `bigint` for its primary key identifier:  
     `Users.user_id` (`bigint`), `Suppliers.supplier_id` (`bigint`), `PurchaseOrders.purchase_order_id` (`bigint`), `Shipments.shipment_id` (`bigint`), `StockTransactions.transaction_id` (`bigint`), `AuditLogs.log_id` (`bigint`).
4. **Monetary Precision Standard:**
   - All monetary amounts in SIMS use `NUMERIC(12, 2)` or `NUMERIC(10, 2)` with exact 2-decimal scale:  
     `PurchaseOrders.total_amount` (`NUMERIC(12, 2)`), `PurchaseOrderItems.subtotal` (`NUMERIC(12, 2)`), `PurchaseOrderItems.unit_price` (`NUMERIC(10, 2)`), `Products.selling_price` (`NUMERIC(10, 2)`).
   - No floating-point (`real`, `double precision`) types are used for financial figures.
5. **Timestamp Standard:**
   - Tables use `TIMESTAMPTZ` (`timestamp with time zone`) with default `NOW()` / `CURRENT_TIMESTAMP` for `created_at` and `updated_at`.
6. **Referential Integrity Constraints:**
   - Critical enterprise tables (`PurchaseOrders`, `StockTransactions`, `AuditLogs`) use `ON DELETE NO ACTION` / `RESTRICT` on user and supplier references to prevent accidental cascading deletion of audit trails or procurement history.
7. **Existing Migration Conventions:**
   - The repository previously lacked a formal `database/migrations` directory or tracking framework. Database access is handled via raw `psycopg2` connections in `backend/app/extensions.py`. The new migration establishes the standard directory: `database/migrations/`.

### 1.2 Assumptions Validated & Clarified
- **Assumption:** Delivery and goods receipt might be recorded on `PurchaseOrders` alone.  
  **Verified Reality:** `PurchaseOrders.status` changes to `'Delivered'` only after a shipment lifecycle is completed. However, physical inspection and goods receipt are specifically recorded in `Shipments.receiving_status` (`'Pending Receipt'`, `'Partially Received'`, `'Fully Received'`) and audited via `StockTransactions` (`transaction_type = 'STOCK_IN'`).
- **Assumption:** Invoices might have a 1:1 constraint with Purchase Orders.  
  **Verified Reality:** Confirmed business decision #6 explicitly requires that **multiple invoices may reference one Purchase Order** (e.g., partial shipments, split goods receipts, milestone billings).

---

## 2. Existing Procurement and Goods-Receipt Relationships

The lifecycle of an inventory procurement transaction in SIMS follows this sequence:

```
[Stock Request] (Owner/Manager creates)
      │
      ▼
[Supplier Quotation] (Supplier submits price & valid_until)
      │ (Owner/Manager approves)
      ▼
[Purchase Order] (Status: Pending -> Accepted)
      │
      ▼
[Shipment] (Supplier creates: Ready for Shipment -> Dispatched -> In Transit -> Delivered)
      │
      ▼
[Goods Receipt / Stock-In] 
      ├── Shipments.receiving_status -> 'Partially Received' | 'Fully Received'
      └── StockTransactions -> transaction_type: 'STOCK_IN', linked to shipment_id & po_id
      │
      ▼ (NEW PHASE 1 DESIGN)
[Supplier Invoice] (Allowed ONLY when Goods Receipt is verified)
      │
      ▼
[Supplier Payment] (Owner/Manager records internal disbursement against approved invoice)
```

### 2.1 Goods-Receipt Eligibility Specification
Business Decision #1 mandates:
> *"Suppliers may submit invoices only after the associated goods have been delivered and goods receipt has been recorded."*

Inspection of `Shipments` and `StockTransactions` confirms that proving delivery and goods receipt requires cross-referencing both entities:

1. **Shipment Delivery Verification:**
   - `Shipments.status = 'Delivered'`
   - `Shipments.delivered_at IS NOT NULL`
2. **Recorded Goods Receipt Verification:**
   - `Shipments.receiving_status IN ('Partially Received', 'Fully Received')`
   - *Note:* Partial receipts remain fully eligible under confirmed MVP decision #1.
3. **Physical Stock Transaction Evidence:**
   - At least one entry in `public."StockTransactions"` where:
     - `transaction_type = 'STOCK_IN'`
     - `purchase_order_id = PurchaseOrders.purchase_order_id`
     - `shipment_id = Shipments.shipment_id`
     - `quantity > 0`

### 2.2 Exact Shipment Matching vs. PO-Level Validation
When a supplier submits an invoice via `POST /api/invoices`, the backend service in Phase 2 must apply strict contextual validation:

#### Case A: If `shipment_id` is explicitly supplied:
The backend **must validate that EXACT shipment** rather than accepting an unrelated qualifying shipment on the same PO:
```sql
SELECT 
    s.shipment_id,
    s.purchase_order_id,
    s.supplier_id,
    s.status AS shipment_status,
    s.receiving_status,
    s.delivered_at,
    COALESCE(SUM(st.quantity), 0) AS total_received_units
FROM "Shipments" s
LEFT JOIN "StockTransactions" st 
    ON s.shipment_id = st.shipment_id 
   AND st.transaction_type = 'STOCK_IN'
WHERE s.shipment_id = %s
GROUP BY s.shipment_id, s.purchase_order_id, s.supplier_id, s.status, s.receiving_status, s.delivered_at;
```
**Required Validations on the Exact Shipment:**
- **Existence:** Shipment must exist. (If not: `404 Shipment not found`).
- **PO Alignment:** `s.purchase_order_id` must match `payload.purchase_order_id`. (If not: `400 Shipment does not belong to specified Purchase Order`).
- **Supplier Alignment:** `s.supplier_id` must match `auth_supplier_id`. (If not: `403 Access denied: Shipment belongs to another supplier`).
- **Delivered Status:** `s.shipment_status` must equal `'Delivered'` and `s.delivered_at` must not be null. (If not: `400 Invoices require delivered shipment status`).
- **Goods Receipt Status:** `s.receiving_status` must be `'Partially Received'` or `'Fully Received'`. (If not: `400 Invoices require recorded goods receipt`).
- **Stock-In Evidence:** `total_received_units` must be `> 0`. (If not: `400 No recorded goods receipt transactions found for this shipment`).

#### Case B: If `shipment_id` is NOT supplied (Invoicing at PO Level):
The backend validates that the parent Purchase Order has at least one qualifying delivered and received shipment belonging to this supplier:
```sql
SELECT 
    s.shipment_id,
    s.status AS shipment_status,
    s.receiving_status,
    COALESCE(SUM(st.quantity), 0) AS total_received_units
FROM "Shipments" s
JOIN "StockTransactions" st 
    ON s.shipment_id = st.shipment_id 
   AND st.transaction_type = 'STOCK_IN'
WHERE s.purchase_order_id = %s
  AND s.supplier_id = %s
  AND s.status = 'Delivered'
  AND s.receiving_status IN ('Partially Received', 'Fully Received')
GROUP BY s.shipment_id, s.status, s.receiving_status
HAVING COALESCE(SUM(st.quantity), 0) > 0;
```
If zero rows are returned, invoice creation is rejected with `400 Bad Request` (*"Invoices can only be submitted after goods have been delivered and receipt has been recorded"*).

---

## 3. Tables and Columns Reused

The new schema reuses existing primary and foreign keys, preserving all relationships without duplicating entities:

| Reused Table | Column Reused | Data Type | Role in Invoicing / Payments |
| :--- | :--- | :--- | :--- |
| `public."Suppliers"` | `supplier_id` | `BIGINT` | Primary vendor identifier for invoice ownership and payment recipient. |
| `public."PurchaseOrders"` | `purchase_order_id` | `BIGINT` | Authoritative procurement order anchor for invoicing. |
| `public."Shipments"` | `shipment_id` | `BIGINT` | Optional delivery reference enabling shipment-specific invoicing when PO has split shipments. |
| `public."Users"` | `user_id` | `BIGINT` | Actor reference: `created_by` for invoice submitter, `recorded_by` for payment disbursing officer. |
| `public."AuditLogs"` | `log_id`, `action`, `table_name`, `record_id`, `user_id` | Standard | Existing audit logging system to be reused in Phase 3 for `INVOICE_SUBMITTED`, `INVOICE_APPROVED`, `PAYMENT_RECORDED`. |

---

## 4. Proposed New Tables, Columns, Constraints, and Indexes

The prepared additive migration introduces two new normalized tables:

### 4.1 Table: `public."SupplierInvoices"`
Stores accounts payable demands submitted by suppliers against verified goods receipts.

| Column Name | Data Type | Nullable | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `invoice_id` | `BIGSERIAL` | NO | Generated | Primary Key. |
| `invoice_number` | `VARCHAR(100)` | NO | None | Supplier-assigned invoice/bill reference number. |
| `supplier_id` | `BIGINT` | NO | None | FK to `"Suppliers"(supplier_id)`. |
| `purchase_order_id`| `BIGINT` | NO | None | FK to `"PurchaseOrders"(purchase_order_id)`. |
| `shipment_id` | `BIGINT` | YES | NULL | Optional FK to `"Shipments"(shipment_id)` for split deliveries. |
| `invoice_date` | `DATE` | NO | None | Invoice issuance date. |
| `due_date` | `DATE` | NO | None | Payment due date. |
| `subtotal` | `NUMERIC(12, 2)`| NO | `0.00` | Net amount before tax (INR). Must be `>= 0.00`. |
| `tax_amount` | `NUMERIC(12, 2)`| NO | `0.00` | Tax amount (GST/VAT in INR). Must be `>= 0.00`. |
| `total_amount` | `NUMERIC(12, 2)`| NO | None | Total payable amount. Must equal `subtotal + tax_amount`. |
| `status` | `VARCHAR(30)` | NO | `'Submitted'` | Status enum check constraint. |
| `rejection_reason` | `TEXT` | YES | NULL | Documented reason if invoice is rejected. |
| `notes` | `TEXT` | YES | NULL | General notes or payment instructions. |
| `created_by` | `BIGINT` | NO | None | FK to `"Users"(user_id)` (actor submitting the invoice). |
| `created_at` | `TIMESTAMPTZ` | NO | `NOW()` | Audit creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | NO | `NOW()` | Audit update timestamp. |

**Constraints (Total: 1 PK + 4 FKs + 2 Unique + 6 Check = 13 Constraints):**
- **Primary Key:**
  - `pk_supplier_invoices`: `PRIMARY KEY (invoice_id)`
- **Foreign Keys (Exactly 4 Foreign Keys):**
  1. `fk_invoice_supplier`: `FOREIGN KEY (supplier_id) REFERENCES public."Suppliers"(supplier_id) ON DELETE RESTRICT ON UPDATE NO ACTION`
  2. `fk_invoice_purchase_order`: `FOREIGN KEY (purchase_order_id) REFERENCES public."PurchaseOrders"(purchase_order_id) ON DELETE RESTRICT ON UPDATE NO ACTION`
  3. `fk_invoice_shipment`: `FOREIGN KEY (shipment_id) REFERENCES public."Shipments"(shipment_id) ON DELETE RESTRICT ON UPDATE NO ACTION`
  4. `fk_invoice_created_by`: `FOREIGN KEY (created_by) REFERENCES public."Users"(user_id) ON DELETE RESTRICT ON UPDATE NO ACTION`
- **Unique Constraints (Exactly 2 Unique Constraints):**
  1. `uq_supplier_invoice_number`: `UNIQUE (supplier_id, invoice_number)` — Guarantees no supplier submits duplicate invoice numbers, while allowing different suppliers to use identical invoice codes.
  2. `uq_supplier_invoice_composite`: `UNIQUE (invoice_id, supplier_id)` — Supports composite foreign key in `SupplierPayments`.
- **Domain Check Constraints (Exactly 6 Check Constraints):**
  1. `chk_invoice_due_date`: `CHECK (due_date >= invoice_date)`
  2. `chk_invoice_subtotal`: `CHECK (subtotal >= 0.00)`
  3. `chk_invoice_tax`: `CHECK (tax_amount >= 0.00)`
  4. `chk_invoice_total_positive`: `CHECK (total_amount > 0.00)`
  5. `chk_invoice_total_consistency`: `CHECK (total_amount = subtotal + tax_amount)`
  6. `chk_invoice_status`: `CHECK (status IN ('Submitted', 'Approved', 'Rejected', 'Partially Paid', 'Paid', 'Cancelled'))`

**Indexes (Exactly 6 Indexes):**
1. `idx_invoices_supplier`: `ON public."SupplierInvoices"(supplier_id)`
2. `idx_invoices_po`: `ON public."SupplierInvoices"(purchase_order_id)`
3. `idx_invoices_shipment`: `ON public."SupplierInvoices"(shipment_id)`
4. `idx_invoices_status`: `ON public."SupplierInvoices"(status)`
5. `idx_invoices_due_date`: `ON public."SupplierInvoices"(due_date)`
6. `idx_invoices_created_at`: `ON public."SupplierInvoices"(created_at DESC)`

---

### 4.2 Table: `public."SupplierPayments"`
Stores internal accounts payable disbursement transactions recorded against approved supplier invoices.

| Column Name | Data Type | Nullable | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `payment_id` | `BIGSERIAL` | NO | Generated | Primary Key. |
| `invoice_id` | `BIGINT` | NO | None | FK to `"SupplierInvoices"(invoice_id)`. |
| `supplier_id` | `BIGINT` | NO | None | FK to `"Suppliers"(supplier_id)`. |
| `payment_date` | `DATE` | NO | None | Date disbursement was executed. |
| `amount_paid` | `NUMERIC(12, 2)`| NO | None | Amount disbursed (INR). Must be `> 0.00`. |
| `payment_method` | `VARCHAR(50)` | NO | None | Banking/disbursement instrument. |
| `payment_reference`| `VARCHAR(100)` | NO | None | Bank UTR, Cheque number, or transaction identifier. |
| `notes` | `TEXT` | YES | NULL | Optional payment remarks. |
| `recorded_by` | `BIGINT` | NO | None | FK to `"Users"(user_id)` (Owner/Manager who logged payment). |
| `created_at` | `TIMESTAMPTZ` | NO | `NOW()` | Record creation timestamp. |

**Constraints (Total: 1 PK + 3 FKs + 2 Check = 6 Constraints):**
- **Primary Key:**
  - `pk_supplier_payments`: `PRIMARY KEY (payment_id)`
- **Foreign Keys (Exactly 3 Foreign Keys):**
  1. `fk_payment_invoice_supplier`: `FOREIGN KEY (invoice_id, supplier_id) REFERENCES public."SupplierInvoices"(invoice_id, supplier_id) ON DELETE RESTRICT ON UPDATE NO ACTION` — **Mathematically guarantees that a payment's `supplier_id` can never diverge from the linked invoice's `supplier_id`**, enforcing database-level supplier isolation.
  2. `fk_payment_supplier`: `FOREIGN KEY (supplier_id) REFERENCES public."Suppliers"(supplier_id) ON DELETE RESTRICT ON UPDATE NO ACTION` — Standalone FK for supplier query plan optimization.
  3. `fk_payment_recorded_by`: `FOREIGN KEY (recorded_by) REFERENCES public."Users"(user_id) ON DELETE RESTRICT ON UPDATE NO ACTION` — FK for the disbursing user.
- **Domain Check Constraints (Exactly 2 Check Constraints):**
  1. `chk_payment_amount`: `CHECK (amount_paid > 0.00)`
  2. `chk_payment_method`: `CHECK (payment_method IN ('Bank Transfer / NEFT', 'RTGS', 'Cheque', 'UPI', 'Wire Transfer', 'Cash', 'Other'))`

**Indexes (Exactly 5 Indexes):**
1. `idx_payments_invoice`: `ON public."SupplierPayments"(invoice_id)`
2. `idx_payments_supplier`: `ON public."SupplierPayments"(supplier_id)`
3. `idx_payments_date`: `ON public."SupplierPayments"(payment_date DESC)`
4. `idx_payments_reference`: `ON public."SupplierPayments"(payment_reference)`
5. `idx_payments_created_at`: `ON public."SupplierPayments"(created_at DESC)`

---

## 5. Architectural Division: Database Constraints vs. Backend Transactional Validations

To preserve the existing live database without executing non-additive or destructive DDL on active production tables, rules are strictly divided between database-enforced constraints and backend service-layer validations.

### 5.1 Enforced at the Database Constraint Level
1. **Primary & Foreign Key Validity:** All references to `Suppliers`, `PurchaseOrders`, `Shipments`, `Users`, and `SupplierInvoices` are enforced with `ON DELETE RESTRICT`.
2. **Payment-to-Invoice Supplier Identity:** Composite FK `fk_payment_invoice_supplier (invoice_id, supplier_id)` mathematically guarantees that a payment cannot reference a different supplier than the invoice.
3. **Per-Supplier Invoice Number Uniqueness:** `uq_supplier_invoice_number (supplier_id, invoice_number)`.
4. **Exact Total Consistency:** `total_amount = subtotal + tax_amount`.
5. **Positive Payment Amounts:** `amount_paid > 0.00`.
6. **Due Date Logic:** `due_date >= invoice_date`.
7. **Lifecycle Enums:** Validates `status` and `payment_method` allowed values.

### 5.2 Enforced at the Backend Transactional Service Layer (Phase 2)
PostgreSQL requires a referenced table to have a `PRIMARY KEY` or `UNIQUE` constraint on composite columns before a composite foreign key can target them. In the live database:
- `"PurchaseOrders"` has PK on `(purchase_order_id)` only (no unique constraint on `(purchase_order_id, supplier_id)`).
- `"Shipments"` has PK on `(shipment_id)` only (no unique constraint on `(shipment_id, purchase_order_id, supplier_id)`).

Altering live tables `"PurchaseOrders"` and `"Shipments"` with composite UNIQUE constraints would require non-additive DDL on active production tables. Therefore, cross-table referential alignment is strictly enforced in the backend service layer:

1. **Supplier-to-Purchase-Order Alignment:**
   - Validates that `invoice.supplier_id == po.supplier_id`.
   - Rejects with `403 Forbidden` if an authenticated supplier attempts to invoice another supplier's PO.
2. **Shipment-to-Purchase-Order and Supplier Alignment:**
   - If `shipment_id` is supplied: validates that `shipment.purchase_order_id == invoice.purchase_order_id` AND `shipment.supplier_id == invoice.supplier_id`.
   - Rejects with `400 Bad Request` if a shipment belongs to a different PO, or `403 Forbidden` if it belongs to another supplier.
3. **Exact Shipment Goods-Receipt Verification:**
   - Validates that the exact shipment is `Delivered`, has `receiving_status IN ('Partially Received', 'Fully Received')`, and possesses matching `STOCK_IN` transactions in `StockTransactions` with `quantity > 0`.
4. **Cumulative Invoice Limit per Purchase Order:**
   - Checks that $\sum \text{total\_amount} \le \text{po.total\_amount}$ across all non-rejected invoices, rejecting or flagging unapproved over-invoicing.
5. **Approval Before Payment:**
   - Payments can **only** be logged against invoices in `'Approved'` or `'Partially Paid'` status. Rejects payments against `'Submitted'`, `'Rejected'`, `'Paid'`, or `'Cancelled'` invoices.
6. **Transaction-Safe Overpayment Prevention:**
   - Row-level lock (`SELECT ... FOR UPDATE`) serializes concurrent payment attempts, derives current remaining balance, and rejects any disbursement where $\text{amount\_paid} > \text{remaining\_balance}$.
7. **Role-Based Access Control & Supplier Isolation:**
   - Owners and Managers have organization-wide visibility.
   - Suppliers are strictly scoped to `supplier_id = resolve_supplier_id_for_user(user_id)`.
   - Employees are completely denied (`403 Forbidden`).

---

## 6. Financial Concurrency and Row-Locking Strategy

Financial systems must prevent race conditions, double payments, and ledger inconsistencies under concurrent execution.

### 6.1 Payment Recording Concurrency (`record_payment`)
When an Owner or Manager records a disbursement against an invoice, concurrent requests could attempt to pay the remaining balance simultaneously, resulting in an overpayment.

**Atomic Transactional Flow:**
```sql
BEGIN;

-- 1. Acquire exclusive row lock on target invoice
SELECT 
    invoice_id, 
    supplier_id, 
    total_amount, 
    status
FROM public."SupplierInvoices"
WHERE invoice_id = %s
FOR UPDATE;

-- 2. Verify invoice status eligibility
-- Must be 'Approved' or 'Partially Paid'.
-- Reject if 'Submitted' (must be approved first), 'Rejected', 'Paid', or 'Cancelled'.

-- 3. Compute current sum of payments for this invoice
SELECT COALESCE(SUM(amount_paid), 0)
FROM public."SupplierPayments"
WHERE invoice_id = %s;

-- 4. Calculate exact remaining balance
-- remaining_balance = invoice.total_amount - current_paid
-- IF payment_amount > remaining_balance THEN
--     ROLLBACK;
--     RAISE EXCEPTION "Payment rejected: amount exceeds remaining balance of %", remaining_balance;

-- 5. Insert new payment record
INSERT INTO public."SupplierPayments" (
    invoice_id,
    supplier_id,
    payment_date,
    amount_paid,
    payment_method,
    payment_reference,
    notes,
    recorded_by,
    created_at
) VALUES (...);

-- 6. Atomically update invoice status
-- new_remaining_balance = remaining_balance - payment_amount
-- IF new_remaining_balance == 0.00 THEN
--     new_status = 'Paid'
-- ELSE
--     new_status = 'Partially Paid'
-- END IF

UPDATE public."SupplierInvoices"
SET status = new_status,
    updated_at = NOW()
WHERE invoice_id = %s;

-- 7. Record Audit Log
-- log_audit_event(action='PAYMENT_RECORDED', table_name='SupplierPayments', record_id=payment_id, ...)

COMMIT;
```

**Concurrency Guarantees:**
- `FOR UPDATE` serializes concurrent transactions on the same invoice; the second transaction blocks until the first commits, reading the updated remaining balance.
- Overpayment is impossible even under high concurrency.
- Invoice status transition is 100% atomic with payment record creation.

### 6.2 Invoice Limit per Purchase Order (`create_invoice`)
Multiple invoices are permitted per Purchase Order (Decision #6). However, cumulative billings should not exceed the agreed PO total without authorization.

**Atomic Transactional Flow:**
```sql
BEGIN;

-- 1. Acquire row lock on parent Purchase Order
SELECT purchase_order_id, supplier_id, total_amount, status
FROM public."PurchaseOrders"
WHERE purchase_order_id = %s
FOR UPDATE;

-- 2. Verify supplier ownership & Goods Receipt eligibility (Section 2.2)

-- 3. Calculate cumulative invoiced amount to date
SELECT COALESCE(SUM(total_amount), 0)
FROM public."SupplierInvoices"
WHERE purchase_order_id = %s
  AND status NOT IN ('Rejected', 'Cancelled');

-- IF cumulative_invoiced + new_invoice_amount > po.total_amount THEN
--     (Flag or reject if invoice exceeds PO contract cap)

-- 4. Insert invoice record with status = 'Submitted'
INSERT INTO public."SupplierInvoices" (...) VALUES (...);

-- 5. Record Audit Log ('INVOICE_SUBMITTED')

COMMIT;
```

### 6.3 Immutable Financial History (Zero Destructive Deletions)
- Financial records are immutable. `DELETE` operations on `SupplierInvoices` or `SupplierPayments` are strictly prohibited.
- If an invoice is rejected, its status becomes `'Rejected'` with mandatory `rejection_reason`.
- If an approved invoice is cancelled, its status becomes `'Cancelled'`.
- Payment records cannot be deleted. Erroneous payments must be corrected via offsetting reversal/credit records.
- Foreign keys specify `ON DELETE RESTRICT`, preventing cascading deletion of suppliers, POs, or users linked to financial transactions.

---

## 7. Status Model and Total-Amount Convention

### 7.1 Status Model
```
[Supplier Submits]
       │
       ▼
   Submitted  ─────────────► Rejected (with rejection_reason)
       │
       │ (Owner/Manager Approves)
       ▼
    Approved
       │
       │ (Partial Disbursement Recorded)
       ▼
  Partially Paid
       │
       │ (Final Disbursement: remaining_balance == 0)
       ▼
      Paid
```

### 7.2 Total-Amount and Tax Convention
$$\text{total\_amount} = \text{subtotal} + \text{tax\_amount}$$

- **`subtotal`:** Base pre-tax commercial value (`NUMERIC(12, 2)`, `>= 0.00`).
- **`tax_amount`:** Applicable GST/VAT (`NUMERIC(12, 2)`, `>= 0.00`, default `0.00`).
- **`total_amount`:** Exact gross payable liability (`NUMERIC(12, 2)`, `> 0.00`).
- **Enforced via Database Constraint:**
  ```sql
  CONSTRAINT chk_invoice_total_consistency CHECK (total_amount = subtotal + tax_amount)
  ```

---

## 8. Migration File Details & Idempotency Behavior

The additive SQL migration is located at:
- [`database/migrations/001_create_supplier_payments_and_invoices.sql`](file:///d:/7even%20repica%202/database/migrations/001_create_supplier_payments_and_invoices.sql)

### 8.1 Summary of Executable SQL Structure:
1. **Explicit Transaction Boundaries:** Wrapped completely in `BEGIN;` and `COMMIT;`.
2. **`public."SupplierInvoices"`:**
   - 16 columns matching exact PostgreSQL SIMS conventions.
   - 4 foreign keys (`ON DELETE RESTRICT`): `fk_invoice_supplier`, `fk_invoice_purchase_order`, `fk_invoice_shipment`, `fk_invoice_created_by`.
   - 2 unique constraints: `uq_supplier_invoice_number`, `uq_supplier_invoice_composite`.
   - 6 check constraints: `chk_invoice_due_date`, `chk_invoice_subtotal`, `chk_invoice_tax`, `chk_invoice_total_positive`, `chk_invoice_total_consistency`, `chk_invoice_status`.
   - Table and column comments.
   - 6 high-frequency query indexes.
3. **`public."SupplierPayments"`:**
   - 10 columns capturing disbursement metadata and references.
   - 3 foreign keys (`ON DELETE RESTRICT`):
     1. Composite FK: `fk_payment_invoice_supplier (invoice_id, supplier_id) REFERENCES public."SupplierInvoices"(invoice_id, supplier_id)`.
     2. Standalone FK: `fk_payment_supplier (supplier_id) REFERENCES public."Suppliers"(supplier_id)`.
     3. Recorded-by FK: `fk_payment_recorded_by (recorded_by) REFERENCES public."Users"(user_id)`.
   - 2 check constraints: `chk_payment_amount`, `chk_payment_method`.
   - Table and column comments.
   - 5 high-frequency query indexes.

### 8.2 Idempotency and Conflict Behavior Notice
The migration uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.
- **Important DBA Notice:** `IF NOT EXISTS` prevents catastrophic syntax crashes if an object name exists, but **it does NOT verify that a pre-existing object has the expected schema definition, columns, or constraint rules**.
- If pre-existing objects with these names were present, the DBA must inspect their DDL rather than blindly assuming compatibility.
- To prevent accidental data loss, **no automatic destructive drop or rebuild logic is included**.
- Preflight inspection (Section 9.1) verified that **zero conflicting objects exist** in the live database.

---

## 9. Preflight Inspection and Static Validation Results

### 9.1 Live Read-Only Preflight Results (Supabase PostgreSQL)
An authorized read-only preflight query was executed against the active Supabase PostgreSQL database:

| Preflight Check | Target Object / Scope | Result | Status |
| :--- | :--- | :--- | :---: |
| **Table Existence** | `SupplierInvoices`, `SupplierPayments`, `Invoices`, `Payments` | `exists = False` for all | **PASSED** (Zero Collisions) |
| **Index Name Collisions** | All 11 proposed index names (`idx_invoices_*`, `idx_payments_*`) | `0 colliding indexes` | **PASSED** (All 11 Available) |
| **Referenced Table Types** | `Suppliers.supplier_id` | `data_type: bigint, PK: Suppliers_pkey` | **PASSED** (Compatible) |
| **Referenced Table Types** | `PurchaseOrders.purchase_order_id` | `data_type: bigint, PK: PurchaseOrders_pkey` | **PASSED** (Compatible) |
| **Referenced Table Types** | `Shipments.shipment_id` | `data_type: bigint, PK: Shipments_pkey` | **PASSED** (Compatible) |
| **Referenced Table Types** | `Users.user_id` | `data_type: bigint, PK: Users_pkey` | **PASSED** (Compatible) |

### 9.2 Static SQL Validation Results
A static validation script inspected `001_create_supplier_payments_and_invoices.sql`:
1. **Transaction Boundaries:** `BEGIN;` and `COMMIT;` present and wrapping all DDL: **PASSED**.
2. **Destructive Statements:** Checked for executable `DROP`, `TRUNCATE`, `ALTER TABLE`, `DELETE FROM`: **PASSED (0 found)**.
3. **Parentheses Balance:** `(` count = 51, `)` count = 51: **PASSED (Balanced)**.
4. **Foreign Key Counts:**
   - `SupplierInvoices`: Exactly 4 foreign keys: **PASSED**.
   - `SupplierPayments`: Exactly 3 foreign keys: **PASSED**.
5. **Unique Constraints:** `SupplierInvoices`: Exactly 2 unique constraints: **PASSED**.
6. **Check Constraints:**
   - `SupplierInvoices`: Exactly 6 check constraints: **PASSED**.
   - `SupplierPayments`: Exactly 2 check constraints: **PASSED**.
7. **Index Count:** Exactly 11 indexes defined with `CREATE INDEX IF NOT EXISTS`: **PASSED**.
8. **Composite FK Target Match:** `(invoice_id, supplier_id)` foreign key matches `UNIQUE (invoice_id, supplier_id)`: **PASSED**.

### 9.3 Exact Decimal Arithmetic & Balance Simulation:
- Invoiced Subtotal `₹12,924.36` + Tax `₹2,326.39` = Total `₹15,250.75`: **PASSED**.
- Partial Payment 1 (`₹5,000.00`) -> Remaining `₹10,250.75` (`Partially Paid`): **PASSED**.
- Partial Payment 2 (`₹7,500.00`) -> Remaining `₹2,750.75` (`Partially Paid`): **PASSED**.
- Final Payment 3 (`₹2,750.75`) -> Remaining `₹0.00` (`Paid`): **PASSED**.
- Overpayment Rejection (attempting `₹1.00` when balance is `0`): **PASSED** (Blocked).

> [!IMPORTANT]
> **Live DDL Execution Confirmation:**  
> In strict accordance with Phase 1 constraints, **zero DDL statements were executed against the live database**. The migration has NOT been applied to live Supabase.

---

## 10. Database Access Security Preflight & Architecture Analysis

An exhaustive, read-only security preflight was performed to evaluate database-access security, Supabase PostgREST Data API exposure, PostgreSQL role privileges, and Row Level Security (RLS) conventions prior to migration approval.

### 10.1 Database Access Model: Strict Backend-Only Architecture
Codebase and configuration inspection confirmed the following architectural facts:
1. **Frontend Network Layer:**
   - Inspection of [api.js](file:///d:/7even%20repica%202/frontend/js/api/api.js) confirms that all client-side network communication is strictly routed through the Flask API gateway (`http://127.0.0.1:5000/api`).
   - The frontend contains **zero** Supabase client library integrations (`@supabase/supabase-js` is not installed or referenced).
   - Zero direct PostgREST or Supabase GraphQL calls exist anywhere in the frontend or admin clients.
2. **Backend Database Connection:**
   - In [extensions.py](file:///d:/7even%20repica%202/backend/app/extensions.py), the Flask application establishes raw PostgreSQL connections via `psycopg2.connect(DATABASE_URL)`.
   - The connection user is `postgres` (`rolsuper = True`, `rolcanlogin = True`, `rolbypassrls = True`).
   - The database server is hosted on Supabase (`db.hltosdkwugwcpofekjgp.supabase.co:5432` / Supabase transaction pooler).
3. **Authentication Boundary:**
   - SIMS user accounts (`public."Users"`) and roles (`public."Roles"`) are purely application-level database records.
   - Authentication is handled exclusively by Flask using `flask_jwt_extended` with a private HMAC secret (`JWT_SECRET_KEY`).
   - SIMS users do **not** exist in Supabase's internal auth system (`auth.users`), and Flask JWTs have **no correlation** with Supabase Auth JWTs.

### 10.2 Supabase Grants, Default Privileges, and PostgREST Data API Exposure Assessment
A direct read-only query was executed against `pg_roles`, `pg_class`, `information_schema.role_table_grants`, and `pg_default_acl`:

| Security Attribute | Inspected Value | Impact on Supplier Invoices & Payments |
| :--- | :--- | :--- |
| **Backend DB User (`postgres`)** | `superuser = True`, `bypassrls = True` | Operates with unrestricted administrative privileges. Bypasses all PostgreSQL Row Level Security. |
| **Supabase PostgREST Roles** | `anon` (`canlogin = False`, `bypassrls = False`)<br>`authenticated` (`canlogin = False`, `bypassrls = False`)<br>`service_role` (`canlogin = False`, `bypassrls = True`) | Roles assumed by Supabase's HTTP Data API (PostgREST) when external requests arrive with public or service keys. |
| **Public Schema Usage** | `has_schema_privilege('anon', 'public', 'USAGE') = True`<br>`has_schema_privilege('authenticated', 'public', 'USAGE') = True` | Both public PostgREST roles have permission to resolve objects in the `public` schema. |
| **Existing Tables RLS Status** | `relrowsecurity = False` on all 19 existing tables (`Users`, `Suppliers`, `PurchaseOrders`, etc.) | None of the existing tables in SIMS have Row Level Security enabled. |
| **Existing Tables RLS Policies** | `0 policies` exist in schema `public` | No database-level row filtering is currently implemented for any table. |
| **Supabase Default Privileges (`pg_default_acl`)** | `role=postgres, namespace=public, type=r`<br>`acl={postgres=arwdDxtm/postgres, anon=arwdDxtm/postgres, authenticated=arwdDxtm/postgres, service_role=arwdDxtm/postgres}` | **CRITICAL:** In Supabase, any table created by `postgres` in `public` automatically grants `SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER` (`arwdDxtm`) to `anon` and `authenticated`! |

#### Exposure Determination:
> [!CAUTION]
> **PostgREST Data API Exposure Finding:**  
> If `001_create_supplier_payments_and_invoices.sql` is executed without enabling Row Level Security or explicitly revoking permissions, **`SupplierInvoices` and `SupplierPayments` would be immediately exposed to the public internet through the Supabase Data API (`https://<project-ref>.supabase.co/rest/v1/`)**!  
> Anyone possessing the project's public Supabase `anon` key would be able to read all supplier invoices, inspect financial disbursement amounts, alter invoice records, or insert unauthorized payment entries—completely bypassing the Flask application and its RBAC middleware.

### 10.3 Verification of Intended Role-Based Access Rules
The business rules governing invoice and payment access must be strictly maintained:

| Role | Financial Access Boundary | Enforcement Mechanism in SIMS |
| :--- | :--- | :--- |
| **Owner** | Full organization-wide visibility into all invoices and payments. May approve/reject invoices and record payments. | Enforced in Flask: `@role_required("Owner", "Manager")` on all financial endpoints. |
| **Manager** | Full organization-wide visibility into all invoices and payments. May approve/reject invoices and record payments. | Enforced in Flask: `@role_required("Owner", "Manager")` on all financial endpoints. |
| **Supplier** | Scoped visibility strictly into their own invoices and payments (`supplier_id = auth_supplier_id`). May submit invoices for delivered/received POs. **Cannot** record payments, approve invoices, or view other suppliers' records. | Enforced in Flask: `@role_required("Supplier")` with service-level `WHERE supplier_id = %s` data filtering. |
| **Employee** | **Zero financial access.** Cannot view invoices or payments. Cannot submit invoices. Cannot record payments. | Enforced in Flask: Requests to `/api/invoices/*` and `/api/payments/*` return HTTP `403 Access Denied`. |

#### Database-Level Enforcement Gap:
Because SIMS uses custom Flask JWTs rather than Supabase Auth tokens, Supabase's PostgREST gateway cannot identify the user's role or `supplier_id`. To PostgREST, incoming HTTP requests arrive as either unauthenticated `anon` requests or generic tokens. Flask RBAC provides zero protection against direct PostgREST database queries.  
Therefore, the database itself must enforce a **default-deny boundary** on PostgREST client roles.

### 10.4 Smallest Safe Security Change Recommendation & Compatibility Proof
To completely seal the Supabase Data API exposure vector without impacting the existing application or database architecture, we recommend the following security hardening change:

```sql
-- Part 1: Enable Row Level Security (Default-Deny for all non-superuser roles)
ALTER TABLE public."SupplierInvoices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."SupplierPayments" ENABLE ROW LEVEL SECURITY;

-- Part 2: Explicitly revoke table privileges from PostgREST client roles & PUBLIC
REVOKE ALL ON TABLE public."SupplierInvoices" FROM anon, authenticated, PUBLIC;
REVOKE ALL ON TABLE public."SupplierPayments" FROM anon, authenticated, PUBLIC;
```

#### Detailed Effective Privilege & Access Matrix:
An inspection of PostgreSQL role inheritance (`pg_auth_members`), system attributes (`rolbypassrls`, `rolsuper`), and privileges verifies the effective access for each role after applying Migration 002:

| Role | Direct Table Privileges | Inherited Privileges (`member_of`) | RLS Enforced? (`rolbypassrls`) | Effective Access to Invoices & Payments |
| :--- | :--- | :--- | :--- | :--- |
| **`anon`** | **NONE** (Explicitly revoked by `REVOKE ALL`) | `[]` (None; `PUBLIC` also holds 0 privileges) | **YES** (`bypassrls = False`)<br>Default-deny (0 policies) | **BLOCKED (Zero Access)**<br>PostgREST queries return `401/403/404`. Cannot read, insert, update, or delete. |
| **`authenticated`** | **NONE** (Explicitly revoked by `REVOKE ALL`) | `[]` (None; `PUBLIC` also holds 0 privileges) | **YES** (`bypassrls = False`)<br>Default-deny (0 policies) | **BLOCKED (Zero Access)**<br>PostgREST queries return `401/403/404`. Cannot read, insert, update, or delete. |
| **`PUBLIC`** | **NONE** (Explicitly revoked by `REVOKE ALL`) | N/A (Pseudo-role for all users) | **YES** | **BLOCKED (Zero Access)** |
| **`service_role`** | `arwdDxtm` (SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER from `pg_default_acl`) | `[]` (None) | **NO** (`bypassrls = True`) | **FULL (Admin Only)**<br>Accessible only via private `service_role` secret (verified unexposed). |
| **`postgres`** (Flask Backend) | **TABLE OWNER** + `arwdDxtm` (Full privileges) | `['supabase_privileged_role', 'pg_read_all_data', ...]` | **NO** (`bypassrls = True`) | **FULL (100% Preserved)**<br>Flask backend maintains uninterrupted read/write access via `psycopg2`. |

#### Compatibility Analysis with Existing Backend Connection:
1. **Superuser / Bypass RLS:** The Flask backend connects via `DATABASE_URL` as user `postgres`. In PostgreSQL, `postgres` possesses `rolbypassrls = True`. By PostgreSQL design, roles with `BYPASSRLS` automatically bypass all table RLS checks.
2. **Table Ownership:** User `postgres` is the owner of both tables. Revoking permissions from `anon`, `authenticated`, and `PUBLIC` has zero effect on the table owner.
3. **Zero Backend Regression:** Every query executed by the Flask backend in Phase 2 (`SELECT`, `INSERT`, `UPDATE`, `FOR UPDATE`) will continue to operate with 100% normal capability and zero performance overhead.
4. **Dual-Layer Defense in Depth:** External HTTP requests attempting to query `https://<project-ref>.supabase.co/rest/v1/SupplierInvoices` or `SupplierPayments` via PostgREST will be rejected at the table grant check and blocked by RLS default-deny.
5. **Zero Impact on Existing Tables:** This change applies strictly to `"SupplierInvoices"` and `"SupplierPayments"`. It does not alter or disrupt any of the existing 19 SIMS tables.

### 10.5 Secondary Index Redundancy Review
A thorough architectural review of the 11 secondary indexes defined in `001_create_supplier_payments_and_invoices.sql` was conducted:

#### 1. Analysis of `idx_invoices_supplier` on `SupplierInvoices`:
- In `001_create_supplier_payments_and_invoices.sql`, the table defines:
  ```sql
  CONSTRAINT uq_supplier_invoice_number UNIQUE (supplier_id, invoice_number)
  ```
- In PostgreSQL B-tree indexing, a composite index on `(supplier_id, invoice_number)` automatically indexes `supplier_id` as its leading prefix column. Any query filtering on `WHERE supplier_id = %s` can utilize `uq_supplier_invoice_number` for an index range scan.
- Therefore, `idx_invoices_supplier ON public."SupplierInvoices"(supplier_id)` is **technically redundant** in terms of query planner access paths.
- **Trade-off Evaluation:**
  - `idx_invoices_supplier` indexes only an 8-byte `BIGINT`, whereas `uq_supplier_invoice_number` indexes `(BIGINT, VARCHAR(100))`. The standalone index is slightly more compact in the buffer cache.
  - However, in an MVP deployment with moderate invoice volume, the storage and write-time overhead of maintaining both is negligible.
  - Per the explicit preflight restriction (*"do not change the migration solely for a speculative performance improvement"*), **we recommend leaving `001_create_supplier_payments_and_invoices.sql` unchanged**. The technical redundancy is documented here for future DBA optimization during large-scale production indexing passes.

#### 2. Analysis of Indexes on `SupplierPayments`:
- `SupplierPayments` defines composite FK `fk_payment_invoice_supplier (invoice_id, supplier_id) REFERENCES "SupplierInvoices"(invoice_id, supplier_id)`.
- However, `SupplierPayments` does **not** have a unique constraint on `(invoice_id, supplier_id)` because multiple partial payments may be recorded for the same invoice and supplier.
- Consequently, there is no composite index covering `(invoice_id, supplier_id)`.
- `idx_payments_invoice` is required for calculating invoice payment balances (`SUM(amount_paid) WHERE invoice_id = %s`).
- `idx_payments_supplier` is required for filtering payments by supplier in the Supplier Portal (`WHERE supplier_id = %s`).
- **Verdict:** Zero redundant indexes exist on `SupplierPayments`.

### 10.6 Proposed Security Hardening Migration Script
In accordance with Task 5, the proposed security hardening SQL has been prepared as a separate standalone migration:
- **File:** [002_secure_supplier_payments_and_invoices_rls.sql](file:///d:/7even%20repica%202/database/migrations/002_secure_supplier_payments_and_invoices_rls.sql)
- **Status:** **PROPOSED / PENDING APPROVAL** (Not applied to live database).

### 10.7 Credential Isolation & Scope Limitations

#### 1. Verification of `service_role` Credential Isolation:
- An exhaustive scan across all frontend directories (`frontend/`, `frontend-admin/`, `frontend-mpa-backup/`), JavaScript bundles, and backend code confirmed that the Supabase `service_role` credential is **completely absent** from client-side files.
- No Supabase API keys (`anon` or `service_role`) are embedded in client code, client local storage, or public repositories.
- Client-facing users have zero access to the `service_role` secret.

#### 2. Scope Boundary of Migration 002:
> [!IMPORTANT]
> **Scope Limitation Notice:**  
> Migration 002 applies **exclusively to the new financial tables** (`SupplierInvoices` and `SupplierPayments`). It explicitly does NOT modify, lock down, or enable RLS on the 19 pre-existing SIMS tables (`Users`, `Suppliers`, `PurchaseOrders`, `Shipments`, etc.).  
> The existing tables currently remain in their baseline state (`relrowsecurity = False`), which is an existing infrastructure characteristic that predates this feature. Securing existing tables requires a separate, dedicated system-wide security assessment and regression testing suite to ensure existing features are not impacted.

### 10.8 Unresolved Security Risks & Phase 2 Backend Guardrails
The following security risks cannot be resolved at the schema layer and require strict enforcement in Phase 2 backend service logic:

1. **PostgREST Exposure on Existing Tables:**
   - Because all 19 pre-existing SIMS tables currently have `relrowsecurity = False` and default grants to `anon`/`authenticated`, the entire database relies on the secrecy of the Supabase project configuration or PostgREST service settings.
   - *Recommendation for Infrastructure/DevOps:* Evaluate disabling the Supabase Data API (PostgREST) in Supabase Project Settings > API > Rest API if SIMS is intended to remain a 100% backend-mediated application.
2. **Phase 2 Service Authorization Guardrails:**
   - Financial endpoints (`/api/invoices`, `/api/payments`) must enforce strict role checks:
     - `@role_required("Owner", "Manager", "Supplier")` on invoice endpoints, with `auth_supplier_id` injected into all queries for Supplier roles.
     - `@role_required("Owner", "Manager")` on payment creation endpoints (`POST /api/payments`).
     - Explicit rejection (HTTP `403 Forbidden`) for Employee roles across all payment and invoice routes.
3. **Concurrent Overpayment Lock:**
   - The backend payment recording service must lock the target invoice row using `SELECT total_amount FROM "SupplierInvoices" WHERE invoice_id = %s FOR UPDATE` inside the database transaction before summing recorded payments and inserting new payments.

---

## 11. Statement of Database and Code Integrity

- **No Live Schema Changes:** Zero DDL statements were executed against the live Supabase PostgreSQL database. No tables or columns were added, modified, or dropped.
- **No Live Data Alteration:** Zero production records were inserted, updated, or deleted.
- **No Application Code Changes:** No Flask routes, backend services, frontend JavaScript files, or configuration settings were modified.
- **Preservation of Previous Work:** Improvement 1 (Employee Transaction Isolation) and Improvement 2 (Stock Request Route Authorization) remain completely functional and untouched.
- **Zero Execution of Migration Files:** Neither `001_create_supplier_payments_and_invoices.sql` nor `002_secure_supplier_payments_and_invoices_rls.sql` has been executed against live Supabase.

---

## 12. Stopping Condition & Exact Next Steps

All security preflight checks, grant inspections, access rule verifications, index reviews, and migration documentations are complete. **Work has stopped in accordance with the security preflight restrictions.**

### Exact Next Steps for User Review & Approval:
1. **Review Deliverables:**
   - Base Schema Migration: [001_create_supplier_payments_and_invoices.sql](file:///d:/7even%20repica%202/database/migrations/001_create_supplier_payments_and_invoices.sql)
   - Proposed Security Hardening Migration: [002_secure_supplier_payments_and_invoices_rls.sql](file:///d:/7even%20repica%202/database/migrations/002_secure_supplier_payments_and_invoices_rls.sql)
   - Comprehensive Preflight Report: [sims_supplier_payments_phase1_schema.md](file:///d:/7even%20repica%202/docs/reports/sims_supplier_payments_phase1_schema.md)
2. **Approval Decision:**
   - Approve applying `001_create_supplier_payments_and_invoices.sql` followed by `002_secure_supplier_payments_and_invoices_rls.sql` (or incorporating the RLS/REVOKE block directly into `001`) against live Supabase PostgreSQL.
   - Authorize proceeding to **Phase 2: Backend Service & API Implementation** upon successful migration execution.

