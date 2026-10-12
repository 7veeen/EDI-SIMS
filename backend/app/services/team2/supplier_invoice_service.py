from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from psycopg2 import Error

from app.extensions import get_db_connection
from app.services.team3.audit_service import log_audit_event


def resolve_supplier_id_for_user(cursor, user_id):
    """
    Resolve the supplier_id for an authenticated user with role Supplier.
    Returns supplier_id (int) or None if not linked.
    """
    try:
        cursor.execute(
            'SELECT supplier_id FROM public."Suppliers" WHERE user_id = %s;',
            (int(user_id),)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _format_decimal(val):
    if val is None:
        return 0.00
    try:
        return float(Decimal(str(val)).quantize(Decimal('0.01')))
    except Exception:
        return float(val)


def _format_date(val):
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return str(val)


def submit_invoice(user_id, role, data):
    """
    Submit a supplier invoice with strict validation and procurement rules.
    - Role constraint: Only authenticated Suppliers can submit invoices.
    - Supplier ID is resolved server-side from user_id; never client-supplied.
    - Verified against PO, shipment delivery, and positive STOCK_IN goods receipt.
    - Cumulative PO amount cap enforced transactionally using FOR UPDATE.
    - Initial status: 'Submitted'.
    """
    if role != "Supplier":
        return None, "Access denied. Only Suppliers can submit invoices.", 403

    if not data or not isinstance(data, dict):
        return None, "Request body must be a valid JSON object", 400

    invoice_number = str(data.get("invoice_number", "")).strip()
    if not invoice_number:
        return None, "invoice_number is required", 400

    po_id_raw = data.get("purchase_order_id")
    if po_id_raw is None:
        return None, "purchase_order_id is required", 400
    try:
        purchase_order_id = int(po_id_raw)
    except (ValueError, TypeError):
        return None, "purchase_order_id must be a valid integer", 400

    shipment_id = None
    shipment_id_raw = data.get("shipment_id")
    if shipment_id_raw not in (None, "", "null"):
        try:
            shipment_id = int(shipment_id_raw)
        except (ValueError, TypeError):
            return None, "shipment_id must be a valid integer", 400

    # Parse and validate dates
    invoice_date_raw = data.get("invoice_date")
    if not invoice_date_raw:
        parsed_invoice_date = date.today()
    else:
        try:
            parsed_invoice_date = datetime.strptime(str(invoice_date_raw).split("T")[0], "%Y-%m-%d").date()
        except ValueError:
            return None, "invoice_date must be in YYYY-MM-DD format", 400

    due_date_raw = data.get("due_date")
    if not due_date_raw:
        return None, "due_date is required", 400
    try:
        parsed_due_date = datetime.strptime(str(due_date_raw).split("T")[0], "%Y-%m-%d").date()
    except ValueError:
        return None, "due_date must be in YYYY-MM-DD format", 400

    if parsed_due_date < parsed_invoice_date:
        return None, "due_date must be on or after invoice_date", 400

    # Parse and validate monetary amounts with exact 2-decimal precision
    try:
        subtotal_val = Decimal(str(data.get("subtotal", "0.00"))).quantize(Decimal("0.01"))
        tax_val = Decimal(str(data.get("tax_amount", "0.00"))).quantize(Decimal("0.01"))
        total_val = Decimal(str(data.get("total_amount", "0.00"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None, "Financial amounts must be valid numeric values", 400

    if subtotal_val < Decimal("0.00"):
        return None, "subtotal cannot be negative", 400
    if tax_val < Decimal("0.00"):
        return None, "tax_amount cannot be negative", 400
    if total_val <= Decimal("0.00"):
        return None, "total_amount must be greater than zero", 400

    if total_val != (subtotal_val + tax_val):
        return None, f"total_amount ({total_val:.2f}) must equal subtotal ({subtotal_val:.2f}) plus tax_amount ({tax_val:.2f})", 400

    notes = data.get("notes")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Resolve Supplier Identity strictly from JWT context
        auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
        if not auth_supplier_id:
            return None, "Access denied. Authenticated user is not linked to an active supplier profile", 403

        # 2. Lock Purchase Order row and verify ownership & status
        cursor.execute(
            '''
            SELECT purchase_order_id, supplier_id, status, total_amount
            FROM public."PurchaseOrders"
            WHERE purchase_order_id = %s
            FOR UPDATE;
            ''',
            (purchase_order_id,)
        )
        po_row = cursor.fetchone()
        if not po_row:
            return None, "Purchase Order not found", 404

        po_supplier_id = po_row[1]
        po_status = po_row[2]
        po_total_amount = Decimal(str(po_row[3])).quantize(Decimal("0.01"))

        if po_supplier_id != auth_supplier_id:
            return None, "Access denied. Purchase Order belongs to another supplier", 403

        if po_status in ("Cancelled", "Draft", "Pending"):
            return None, f"Cannot submit invoice for Purchase Order in '{po_status}' status", 400

        # 3. Goods-Receipt Eligibility Verification
        if shipment_id is not None:
            # Case A: Exact shipment supplied -> Must validate that exact shipment
            cursor.execute(
                '''
                SELECT 
                    s.shipment_id,
                    s.purchase_order_id,
                    s.supplier_id,
                    s.status,
                    s.receiving_status,
                    s.delivered_at,
                    COALESCE(SUM(st.quantity), 0) AS total_received_units
                FROM public."Shipments" s
                LEFT JOIN public."StockTransactions" st 
                    ON s.shipment_id = st.shipment_id 
                   AND st.transaction_type = 'STOCK_IN'
                WHERE s.shipment_id = %s
                GROUP BY s.shipment_id, s.purchase_order_id, s.supplier_id, s.status, s.receiving_status, s.delivered_at;
                ''',
                (shipment_id,)
            )
            sh_row = cursor.fetchone()
            if not sh_row:
                return None, "Shipment not found", 404

            sh_po_id = sh_row[1]
            sh_supplier_id = sh_row[2]
            sh_status = sh_row[3]
            sh_receiving_status = sh_row[4]
            sh_delivered_at = sh_row[5]
            sh_received_units = sh_row[6]

            if sh_po_id != purchase_order_id:
                return None, "Shipment does not belong to specified Purchase Order", 400

            if sh_supplier_id != auth_supplier_id:
                return None, "Access denied. Shipment belongs to another supplier", 403

            if sh_status != "Delivered" or sh_delivered_at is None:
                return None, "Shipment must be delivered before an invoice can be submitted", 400

            if sh_receiving_status not in ("Partially Received", "Fully Received"):
                return None, "Goods receipt has not been recorded for this shipment (must be Partially Received or Fully Received)", 400

            if sh_received_units <= 0:
                return None, "No qualifying goods receipt stock-in transactions found for this shipment", 400
        else:
            # Case B: Invoicing at PO level -> Verify at least one qualifying delivered & received shipment exists
            cursor.execute(
                '''
                SELECT s.shipment_id
                FROM public."Shipments" s
                JOIN public."StockTransactions" st 
                    ON s.shipment_id = st.shipment_id 
                   AND st.transaction_type = 'STOCK_IN'
                WHERE s.purchase_order_id = %s
                  AND s.supplier_id = %s
                  AND s.status = 'Delivered'
                  AND s.receiving_status IN ('Partially Received', 'Fully Received')
                  AND s.delivered_at IS NOT NULL
                  AND st.quantity > 0
                LIMIT 1;
                ''',
                (purchase_order_id, auth_supplier_id)
            )
            qualifying_sh = cursor.fetchone()
            if not qualifying_sh:
                return None, "Invoices can only be submitted after associated goods have been delivered and goods receipt has been officially recorded", 400

        # 4. Check Duplicate Invoice Number for this supplier
        cursor.execute(
            '''
            SELECT invoice_id 
            FROM public."SupplierInvoices" 
            WHERE supplier_id = %s AND invoice_number = %s;
            ''',
            (auth_supplier_id, invoice_number)
        )
        if cursor.fetchone():
            return None, f"Invoice number '{invoice_number}' already exists for your supplier account", 409

        # 5. Enforce Cumulative Purchase Order Cap
        cursor.execute(
            '''
            SELECT COALESCE(SUM(total_amount), 0.00)
            FROM public."SupplierInvoices"
            WHERE purchase_order_id = %s
              AND status NOT IN ('Rejected', 'Cancelled');
            ''',
            (purchase_order_id,)
        )
        existing_invoiced = Decimal(str(cursor.fetchone()[0])).quantize(Decimal("0.01"))
        cumulative_invoiced = existing_invoiced + total_val

        if cumulative_invoiced > po_total_amount:
            remaining_cap = max(Decimal("0.00"), po_total_amount - existing_invoiced)
            return None, (
                f"Cumulative invoice total (₹{cumulative_invoiced:.2f}) would exceed "
                f"Purchase Order total (₹{po_total_amount:.2f}). "
                f"Remaining allowable invoice balance: ₹{remaining_cap:.2f}"
            ), 400

        # 6. Insert Supplier Invoice
        cursor.execute(
            '''
            INSERT INTO public."SupplierInvoices" (
                invoice_number,
                supplier_id,
                purchase_order_id,
                shipment_id,
                invoice_date,
                due_date,
                subtotal,
                tax_amount,
                total_amount,
                status,
                notes,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Submitted', %s, %s)
            RETURNING invoice_id, created_at, updated_at;
            ''',
            (
                invoice_number,
                auth_supplier_id,
                purchase_order_id,
                shipment_id,
                parsed_invoice_date,
                parsed_due_date,
                subtotal_val,
                tax_val,
                total_val,
                notes,
                int(user_id)
            )
        )
        new_row = cursor.fetchone()
        invoice_id = new_row[0]
        created_at = new_row[1]
        updated_at = new_row[2]

        # 7. Record Audit Log inside transaction
        log_audit_event(
            action="INVOICE_SUBMITTED",
            table_name="SupplierInvoices",
            record_id=invoice_id,
            user_id=int(user_id),
            cursor=cursor
        )

        conn.commit()

        # Non-blocking notification dispatch to active Owners and Managers (excluding acting user)
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_active_managers_and_owners
            )
            recipients = get_active_managers_and_owners(exclude_user_id=user_id)
            for r_uid in recipients:
                create_notification(
                    user_id=r_uid,
                    title="New Invoice Submitted",
                    message=f"Supplier submitted invoice {invoice_number} for Purchase Order #{purchase_order_id} (Total: ₹{total_val:.2f}).",
                    notification_type="Invoice",
                    priority="Normal",
                    reference_type="Invoice",
                    reference_id=invoice_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to dispatch invoice submission notifications: {notif_err}", flush=True)

        invoice_record = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "supplier_id": auth_supplier_id,
            "purchase_order_id": purchase_order_id,
            "shipment_id": shipment_id,
            "invoice_date": _format_date(parsed_invoice_date),
            "due_date": _format_date(parsed_due_date),
            "subtotal": _format_decimal(subtotal_val),
            "tax_amount": _format_decimal(tax_val),
            "total_amount": _format_decimal(total_val),
            "status": "Submitted",
            "notes": notes,
            "created_by": int(user_id),
            "created_at": _format_date(created_at),
            "updated_at": _format_date(updated_at),
            "total_paid": 0.00,
            "remaining_balance": _format_decimal(total_val)
        }

        return invoice_record, None, 201

    except Error as db_err:
        if conn:
            conn.rollback()
        return None, f"Database error during invoice submission: {str(db_err)}", 500
    except Exception as ex:
        if conn:
            conn.rollback()
        return None, f"Unexpected error during invoice submission: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_invoices(user_id, role, status=None, supplier_id_filter=None, po_id=None,
                 date_from=None, date_to=None, search=None, page=1, limit=50):
    """
    List supplier invoices with role-based visibility and supplier isolation.
    - Owner/Manager: Organization-wide access with optional filtering.
    - Supplier: Strictly isolated to their own supplier records.
    - Employee: Access denied (403).
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. You do not have permission to access financial invoices.", 403

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Enforce Supplier Isolation
        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return {"invoices": [], "stats": {"total_invoices": 0, "total_amount": 0.0, "total_paid": 0.0, "total_outstanding": 0.0}, "total_count": 0}, None, 200
            target_supplier_id = auth_supplier_id
        else:
            try:
                target_supplier_id = int(supplier_id_filter) if supplier_id_filter else None
            except (ValueError, TypeError):
                target_supplier_id = None

        query = '''
            SELECT 
                si.invoice_id,
                si.invoice_number,
                si.supplier_id,
                s.supplier_name,
                si.purchase_order_id,
                ('PO-' || po.purchase_order_id::text) AS po_number,
                po.total_amount AS po_total,
                si.shipment_id,
                sh.tracking_number,
                si.invoice_date,
                si.due_date,
                si.subtotal,
                si.tax_amount,
                si.total_amount,
                si.status,
                si.rejection_reason,
                si.notes,
                si.created_by,
                u.username AS created_by_name,
                si.created_at,
                si.updated_at,
                COALESCE(SUM(sp.amount_paid), 0.00) AS total_paid
            FROM public."SupplierInvoices" si
            JOIN public."Suppliers" s ON si.supplier_id = s.supplier_id
            JOIN public."PurchaseOrders" po ON si.purchase_order_id = po.purchase_order_id
            LEFT JOIN public."Shipments" sh ON si.shipment_id = sh.shipment_id
            JOIN public."Users" u ON si.created_by = u.user_id
            LEFT JOIN public."SupplierPayments" sp ON si.invoice_id = sp.invoice_id
            WHERE 1=1
        '''
        params = []

        if target_supplier_id is not None:
            query += ' AND si.supplier_id = %s'
            params.append(target_supplier_id)

        if status:
            clean_status = str(status).strip()
            query += ' AND si.status ILIKE %s'
            params.append(clean_status)

        if po_id:
            try:
                query += ' AND si.purchase_order_id = %s'
                params.append(int(po_id))
            except (ValueError, TypeError):
                pass

        if date_from:
            query += ' AND si.invoice_date >= %s'
            params.append(str(date_from).split("T")[0])

        if date_to:
            query += ' AND si.invoice_date <= %s'
            params.append(str(date_to).split("T")[0])

        if search:
            search_param = f"%{str(search).strip()}%"
            query += ' AND (si.invoice_number ILIKE %s OR s.supplier_name ILIKE %s OR po.purchase_order_id::text ILIKE %s)'
            params.extend([search_param, search_param, search_param])

        query += '''
            GROUP BY 
                si.invoice_id, si.invoice_number, si.supplier_id, s.supplier_name,
                si.purchase_order_id, po.purchase_order_id, po.total_amount,
                si.shipment_id, sh.tracking_number, si.invoice_date, si.due_date,
                si.subtotal, si.tax_amount, si.total_amount, si.status,
                si.rejection_reason, si.notes, si.created_by, u.username,
                si.created_at, si.updated_at
            ORDER BY si.created_at DESC
        '''

        # Pagination calculations
        try:
            page = max(1, int(page))
            limit = max(1, min(200, int(limit)))
        except (ValueError, TypeError):
            page = 1
            limit = 50

        offset = (page - 1) * limit

        cursor.execute(query, tuple(params))
        all_rows = cursor.fetchall()
        total_count = len(all_rows)

        # Summary KPIs
        stat_total_amount = Decimal("0.00")
        stat_total_paid = Decimal("0.00")
        stat_counts = {
            "Submitted": 0,
            "Approved": 0,
            "Rejected": 0,
            "Partially Paid": 0,
            "Paid": 0,
            "Cancelled": 0
        }

        for r in all_rows:
            inv_total = Decimal(str(r[13]))
            inv_paid = Decimal(str(r[21]))
            inv_status = r[14]
            if inv_status != "Cancelled" and inv_status != "Rejected":
                stat_total_amount += inv_total
                stat_total_paid += inv_paid
            if inv_status in stat_counts:
                stat_counts[inv_status] += 1

        paged_rows = all_rows[offset : offset + limit]

        invoices_list = []
        for r in paged_rows:
            t_amt = Decimal(str(r[13]))
            t_paid = Decimal(str(r[21]))
            rem_bal = max(Decimal("0.00"), t_amt - t_paid)

            invoices_list.append({
                "invoice_id": r[0],
                "invoice_number": r[1],
                "supplier_id": r[2],
                "supplier_name": r[3],
                "purchase_order_id": r[4],
                "po_number": r[5],
                "po_total": _format_decimal(r[6]),
                "shipment_id": r[7],
                "tracking_number": r[8],
                "invoice_date": _format_date(r[9]),
                "due_date": _format_date(r[10]),
                "subtotal": _format_decimal(r[11]),
                "tax_amount": _format_decimal(r[12]),
                "total_amount": _format_decimal(t_amt),
                "status": r[14],
                "rejection_reason": r[15],
                "notes": r[16],
                "created_by": r[17],
                "created_by_name": r[18],
                "created_at": _format_date(r[19]),
                "updated_at": _format_date(r[20]),
                "total_paid": _format_decimal(t_paid),
                "remaining_balance": _format_decimal(rem_bal)
            })

        stats = {
            "total_invoices": total_count,
            "total_amount": _format_decimal(stat_total_amount),
            "total_paid": _format_decimal(stat_total_paid),
            "total_outstanding": _format_decimal(stat_total_amount - stat_total_paid),
            "status_counts": stat_counts,
            "page": page,
            "limit": limit
        }

        return {"invoices": invoices_list, "stats": stats, "total_count": total_count}, None, 200

    except Error as db_err:
        return None, f"Database error listing invoices: {str(db_err)}", 500
    except Exception as ex:
        return None, f"Unexpected error listing invoices: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_invoice_by_id(invoice_id, user_id, role):
    """
    Retrieve single invoice details including linked PO, shipment, and payment records.
    - Owner/Manager: Full access.
    - Supplier: Strictly isolated to own supplier ID.
    - Employee: Access denied.
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. You do not have permission to view financial invoices.", 403

    try:
        inv_id = int(invoice_id)
    except (ValueError, TypeError):
        return None, "Invalid invoice_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return None, "Access denied. Authenticated user is not linked to a supplier profile", 403
        else:
            auth_supplier_id = None

        cursor.execute(
            '''
            SELECT 
                si.invoice_id,
                si.invoice_number,
                si.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                si.purchase_order_id,
                ('PO-' || po.purchase_order_id::text) AS po_number,
                po.total_amount AS po_total,
                po.status AS po_status,
                si.shipment_id,
                sh.tracking_number,
                sh.status AS shipment_status,
                sh.receiving_status,
                sh.delivered_at,
                si.invoice_date,
                si.due_date,
                si.subtotal,
                si.tax_amount,
                si.total_amount,
                si.status,
                si.rejection_reason,
                si.notes,
                si.created_by,
                u.username AS created_by_name,
                si.created_at,
                si.updated_at
            FROM public."SupplierInvoices" si
            JOIN public."Suppliers" s ON si.supplier_id = s.supplier_id
            JOIN public."PurchaseOrders" po ON si.purchase_order_id = po.purchase_order_id
            LEFT JOIN public."Shipments" sh ON si.shipment_id = sh.shipment_id
            JOIN public."Users" u ON si.created_by = u.user_id
            WHERE si.invoice_id = %s;
            ''',
            (inv_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Invoice not found", 404

        invoice_supplier_id = row[2]
        if role == "Supplier" and invoice_supplier_id != auth_supplier_id:
            return None, "Access denied. Invoice belongs to another supplier", 403

        # Retrieve payments recorded against this invoice
        cursor.execute(
            '''
            SELECT 
                sp.payment_id,
                sp.payment_date,
                sp.amount_paid,
                sp.payment_method,
                sp.payment_reference,
                sp.notes,
                sp.recorded_by,
                u.username AS recorded_by_name,
                sp.created_at
            FROM public."SupplierPayments" sp
            JOIN public."Users" u ON sp.recorded_by = u.user_id
            WHERE sp.invoice_id = %s
            ORDER BY sp.payment_date DESC, sp.created_at DESC;
            ''',
            (inv_id,)
        )
        payment_rows = cursor.fetchall()
        payments_list = []
        total_paid = Decimal("0.00")

        for pr in payment_rows:
            p_amt = Decimal(str(pr[2]))
            total_paid += p_amt
            payments_list.append({
                "payment_id": pr[0],
                "payment_date": _format_date(pr[1]),
                "amount_paid": _format_decimal(p_amt),
                "payment_method": pr[3],
                "payment_reference": pr[4],
                "notes": pr[5],
                "recorded_by": pr[6],
                "recorded_by_name": pr[7],
                "created_at": _format_date(pr[8])
            })

        t_amt = Decimal(str(row[20]))
        rem_bal = max(Decimal("0.00"), t_amt - total_paid)

        invoice_data = {
            "invoice_id": row[0],
            "invoice_number": row[1],
            "supplier_id": row[2],
            "supplier_name": row[3],
            "supplier_contact": {
                "contact_person": row[4],
                "email": row[5],
                "phone": row[6]
            },
            "purchase_order": {
                "purchase_order_id": row[7],
                "po_number": row[8],
                "po_total": _format_decimal(row[9]),
                "po_status": row[10]
            },
            "shipment": {
                "shipment_id": row[11],
                "tracking_number": row[12],
                "status": row[13],
                "receiving_status": row[14],
                "delivered_at": _format_date(row[15])
            } if row[11] else None,
            "invoice_date": _format_date(row[16]),
            "due_date": _format_date(row[17]),
            "subtotal": _format_decimal(row[18]),
            "tax_amount": _format_decimal(row[19]),
            "total_amount": _format_decimal(t_amt),
            "status": row[21],
            "rejection_reason": row[22],
            "notes": row[23],
            "created_by": row[24],
            "created_by_name": row[25],
            "created_at": _format_date(row[26]),
            "updated_at": _format_date(row[27]),
            "total_paid": _format_decimal(total_paid),
            "remaining_balance": _format_decimal(rem_bal),
            "payment_count": len(payments_list),
            "payments": payments_list
        }

        return {"invoice": invoice_data}, None, 200

    except Error as db_err:
        return None, f"Database error retrieving invoice: {str(db_err)}", 500
    except Exception as ex:
        return None, f"Unexpected error retrieving invoice: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def approve_invoice(invoice_id, user_id, role):
    """
    Approve a submitted invoice.
    - Owner and Manager only.
    - Status must be 'Submitted'.
    - Updates status to 'Approved' atomically.
    """
    if role not in ("Owner", "Manager"):
        return None, "Access denied. Only Owners and Managers can approve invoices.", 403

    try:
        inv_id = int(invoice_id)
    except (ValueError, TypeError):
        return None, "Invalid invoice_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT invoice_id, invoice_number, status, total_amount, supplier_id
            FROM public."SupplierInvoices"
            WHERE invoice_id = %s
            FOR UPDATE;
            ''',
            (inv_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Invoice not found", 404

        current_status = row[2]
        if current_status != "Submitted":
            return None, f"Cannot approve invoice with status '{current_status}'. Only 'Submitted' invoices can be approved.", 400

        cursor.execute(
            '''
            UPDATE public."SupplierInvoices"
            SET status = 'Approved', updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = %s
            RETURNING updated_at;
            ''',
            (inv_id,)
        )
        updated_at = cursor.fetchone()[0]

        log_audit_event(
            action="INVOICE_APPROVED",
            table_name="SupplierInvoices",
            record_id=inv_id,
            user_id=int(user_id),
            cursor=cursor
        )

        conn.commit()

        # Non-blocking notification dispatch to Supplier
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_supplier_user_id
            )
            supplier_user_id = get_supplier_user_id(row[4])
            if supplier_user_id:
                create_notification(
                    user_id=supplier_user_id,
                    title="Invoice Approved",
                    message=f"Your invoice {row[1]} has been approved.",
                    notification_type="Invoice",
                    priority="Normal",
                    reference_type="Invoice",
                    reference_id=inv_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to dispatch invoice approval notification: {notif_err}", flush=True)

        return {
            "message": "Invoice approved successfully",
            "invoice_id": inv_id,
            "invoice_number": row[1],
            "status": "Approved",
            "updated_at": _format_date(updated_at)
        }, None, 200

    except Error as db_err:
        if conn:
            conn.rollback()
        return None, f"Database error approving invoice: {str(db_err)}", 500
    except Exception as ex:
        if conn:
            conn.rollback()
        return None, f"Unexpected error approving invoice: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def reject_invoice(invoice_id, user_id, role, rejection_reason):
    """
    Reject a submitted invoice with mandatory reason.
    - Owner and Manager only.
    - Status must be 'Submitted'.
    - Updates status to 'Rejected' and records rejection_reason.
    """
    if role not in ("Owner", "Manager"):
        return None, "Access denied. Only Owners and Managers can reject invoices.", 403

    try:
        inv_id = int(invoice_id)
    except (ValueError, TypeError):
        return None, "Invalid invoice_id", 400

    clean_reason = str(rejection_reason or "").strip()
    if not clean_reason:
        return None, "rejection_reason is required when rejecting an invoice", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT invoice_id, invoice_number, status, supplier_id
            FROM public."SupplierInvoices"
            WHERE invoice_id = %s
            FOR UPDATE;
            ''',
            (inv_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Invoice not found", 404

        current_status = row[2]
        if current_status != "Submitted":
            return None, f"Cannot reject invoice with status '{current_status}'. Only 'Submitted' invoices can be rejected.", 400

        cursor.execute(
            '''
            UPDATE public."SupplierInvoices"
            SET status = 'Rejected', rejection_reason = %s, updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = %s
            RETURNING updated_at;
            ''',
            (clean_reason, inv_id)
        )
        updated_at = cursor.fetchone()[0]

        log_audit_event(
            action="INVOICE_REJECTED",
            table_name="SupplierInvoices",
            record_id=inv_id,
            user_id=int(user_id),
            cursor=cursor
        )

        conn.commit()

        # Non-blocking notification dispatch to Supplier (with rejection reason)
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_supplier_user_id
            )
            supplier_user_id = get_supplier_user_id(row[3])
            if supplier_user_id:
                create_notification(
                    user_id=supplier_user_id,
                    title="Invoice Rejected",
                    message=f"Your invoice {row[1]} was rejected. Reason: {clean_reason}",
                    notification_type="Invoice",
                    priority="High",
                    reference_type="Invoice",
                    reference_id=inv_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to dispatch invoice rejection notification: {notif_err}", flush=True)

        return {
            "message": "Invoice rejected successfully",
            "invoice_id": inv_id,
            "invoice_number": row[1],
            "status": "Rejected",
            "rejection_reason": clean_reason,
            "updated_at": _format_date(updated_at)
        }, None, 200

    except Error as db_err:
        if conn:
            conn.rollback()
        return None, f"Database error rejecting invoice: {str(db_err)}", 500
    except Exception as ex:
        if conn:
            conn.rollback()
        return None, f"Unexpected error rejecting invoice: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def cancel_invoice(invoice_id, user_id, role, reason=None):
    """
    Cancel an invoice where permitted by business rules:
    - Supplier: Can cancel their own invoice only while status is 'Submitted'.
    - Owner/Manager: Can cancel if status is 'Submitted' or 'Approved', provided zero payments have been recorded.
    - Invoices with recorded payments (Partially Paid, Paid) CANNOT be cancelled.
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. You do not have permission to cancel invoices.", 403

    try:
        inv_id = int(invoice_id)
    except (ValueError, TypeError):
        return None, "Invalid invoice_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return None, "Access denied. User not linked to an active supplier profile", 403
        else:
            auth_supplier_id = None

        cursor.execute(
            '''
            SELECT invoice_id, supplier_id, invoice_number, status, notes
            FROM public."SupplierInvoices"
            WHERE invoice_id = %s
            FOR UPDATE;
            ''',
            (inv_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Invoice not found", 404

        inv_supplier_id = row[1]
        inv_number = row[2]
        current_status = row[3]
        current_notes = row[4] or ""

        if role == "Supplier":
            if inv_supplier_id != auth_supplier_id:
                return None, "Access denied. Invoice belongs to another supplier", 403
            if current_status != "Submitted":
                return None, f"Suppliers can only cancel invoices in 'Submitted' status (current status: '{current_status}')", 400
        else:
            if current_status not in ("Submitted", "Approved"):
                return None, f"Cannot cancel invoice in '{current_status}' status", 400

        # Verify zero payments exist
        cursor.execute(
            '''
            SELECT COUNT(*) FROM public."SupplierPayments" WHERE invoice_id = %s;
            ''',
            (inv_id,)
        )
        payment_count = cursor.fetchone()[0]
        if payment_count > 0:
            return None, "Cannot cancel invoice with recorded payments", 400

        cancel_note = f" [Cancelled: {reason.strip()}]" if reason and str(reason).strip() else " [Cancelled]"
        updated_notes = (current_notes + cancel_note).strip()

        cursor.execute(
            '''
            UPDATE public."SupplierInvoices"
            SET status = 'Cancelled', notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = %s
            RETURNING updated_at;
            ''',
            (updated_notes, inv_id)
        )
        updated_at = cursor.fetchone()[0]

        log_audit_event(
            action="INVOICE_CANCELLED",
            table_name="SupplierInvoices",
            record_id=inv_id,
            user_id=int(user_id),
            cursor=cursor
        )

        conn.commit()

        # Non-blocking notification dispatch
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_active_managers_and_owners,
                get_supplier_user_id
            )
            if role == "Supplier":
                recipients = get_active_managers_and_owners(exclude_user_id=user_id)
                for r_uid in recipients:
                    create_notification(
                        user_id=r_uid,
                        title="Invoice Cancelled",
                        message=f"Supplier cancelled invoice {inv_number}.",
                        notification_type="Invoice",
                        priority="Normal",
                        reference_type="Invoice",
                        reference_id=inv_id
                    )
            else:
                supplier_user_id = get_supplier_user_id(inv_supplier_id)
                if supplier_user_id:
                    create_notification(
                        user_id=supplier_user_id,
                        title="Invoice Cancelled",
                        message=f"Invoice {inv_number} was cancelled by management.",
                        notification_type="Invoice",
                        priority="Normal",
                        reference_type="Invoice",
                        reference_id=inv_id
                    )
                other_mgrs = get_active_managers_and_owners(exclude_user_id=user_id)
                for r_uid in other_mgrs:
                    create_notification(
                        user_id=r_uid,
                        title="Invoice Cancelled",
                        message=f"Invoice {inv_number} was cancelled by management.",
                        notification_type="Invoice",
                        priority="Normal",
                        reference_type="Invoice",
                        reference_id=inv_id
                    )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to dispatch invoice cancellation notifications: {notif_err}", flush=True)

        return {
            "message": "Invoice cancelled successfully",
            "invoice_id": inv_id,
            "invoice_number": inv_number,
            "status": "Cancelled",
            "updated_at": _format_date(updated_at)
        }, None, 200

    except Error as db_err:
        if conn:
            conn.rollback()
        return None, f"Database error cancelling invoice: {str(db_err)}", 500
    except Exception as ex:
        if conn:
            conn.rollback()
        return None, f"Unexpected error cancelling invoice: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
