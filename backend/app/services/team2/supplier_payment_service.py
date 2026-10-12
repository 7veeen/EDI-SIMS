from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from psycopg2 import Error

from app.extensions import get_db_connection
from app.services.team3.audit_service import log_audit_event
from app.services.team2.supplier_invoice_service import resolve_supplier_id_for_user


VALID_PAYMENT_METHODS = (
    'Bank Transfer / NEFT',
    'RTGS',
    'Cheque',
    'UPI',
    'Wire Transfer',
    'Cash',
    'Other'
)


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


def record_payment(user_id, role, data):
    """
    Record an accounts payable disbursement against an approved supplier invoice.
    - Role constraint: Only Owners and Managers can record payments.
    - Invoices must be in 'Approved' or 'Partially Paid' status.
    - Prevents overpayment using transactional row-locking (SELECT ... FOR UPDATE).
    - Updates invoice status to 'Partially Paid' or 'Paid' atomically in the same transaction.
    - Strictly prevents zero, negative, or over-balance disbursements.
    """
    if role not in ("Owner", "Manager"):
        return None, "Access denied. Only Owners and Managers can record payments.", 403

    if not data or not isinstance(data, dict):
        return None, "Request body must be a valid JSON object", 400

    invoice_id_raw = data.get("invoice_id")
    if invoice_id_raw is None:
        return None, "invoice_id is required", 400
    try:
        invoice_id = int(invoice_id_raw)
    except (ValueError, TypeError):
        return None, "invoice_id must be a valid integer", 400

    # Parse and validate amount
    amount_raw = data.get("amount_paid")
    if amount_raw is None:
        return None, "amount_paid is required", 400
    try:
        amount_paid = Decimal(str(amount_raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None, "amount_paid must be a valid numeric amount", 400

    if amount_paid <= Decimal("0.00"):
        return None, "amount_paid must be greater than zero", 400

    # Validate payment method
    payment_method = str(data.get("payment_method", "")).strip()
    if not payment_method:
        return None, f"payment_method is required (must be one of: {', '.join(VALID_PAYMENT_METHODS)})", 400
    if payment_method not in VALID_PAYMENT_METHODS:
        return None, f"Invalid payment_method '{payment_method}'. Allowed methods: {', '.join(VALID_PAYMENT_METHODS)}", 400

    # Validate payment reference (UTR, Cheque number, etc.)
    payment_reference = str(data.get("payment_reference", "")).strip()
    if not payment_reference:
        return None, "payment_reference is required (e.g., UTR number, cheque number, or transaction reference)", 400

    # Parse payment date
    payment_date_raw = data.get("payment_date")
    if not payment_date_raw:
        parsed_payment_date = date.today()
    else:
        try:
            parsed_payment_date = datetime.strptime(str(payment_date_raw).split("T")[0], "%Y-%m-%d").date()
        except ValueError:
            return None, "payment_date must be in YYYY-MM-DD format", 400

    notes = data.get("notes")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Lock invoice row and verify status
        cursor.execute(
            '''
            SELECT invoice_id, supplier_id, invoice_number, total_amount, status
            FROM public."SupplierInvoices"
            WHERE invoice_id = %s
            FOR UPDATE;
            ''',
            (invoice_id,)
        )
        inv_row = cursor.fetchone()
        if not inv_row:
            return None, "Invoice not found", 404

        supplier_id = inv_row[1]
        invoice_number = inv_row[2]
        total_amount = Decimal(str(inv_row[3])).quantize(Decimal("0.01"))
        invoice_status = inv_row[4]

        if invoice_status not in ("Approved", "Partially Paid"):
            return None, (
                f"Payments can only be recorded against 'Approved' or 'Partially Paid' invoices "
                f"(current invoice status: '{invoice_status}')"
            ), 400

        # 2. Concurrency-Safe Outstanding Balance Calculation
        cursor.execute(
            '''
            SELECT COALESCE(SUM(amount_paid), 0.00)
            FROM public."SupplierPayments"
            WHERE invoice_id = %s;
            ''',
            (invoice_id,)
        )
        existing_paid = Decimal(str(cursor.fetchone()[0])).quantize(Decimal("0.01"))
        remaining_balance = total_amount - existing_paid

        if remaining_balance <= Decimal("0.00"):
            return None, f"Invoice '{invoice_number}' is already fully paid", 400

        if amount_paid > remaining_balance:
            return None, (
                f"Payment amount (₹{amount_paid:.2f}) exceeds remaining invoice balance "
                f"(₹{remaining_balance:.2f}). Total invoiced: ₹{total_amount:.2f}, "
                f"already paid: ₹{existing_paid:.2f}."
            ), 400

        # 3. Insert Payment Record
        cursor.execute(
            '''
            INSERT INTO public."SupplierPayments" (
                invoice_id,
                supplier_id,
                payment_date,
                amount_paid,
                payment_method,
                payment_reference,
                notes,
                recorded_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING payment_id, created_at;
            ''',
            (
                invoice_id,
                supplier_id,
                parsed_payment_date,
                amount_paid,
                payment_method,
                payment_reference,
                notes,
                int(user_id)
            )
        )
        pay_row = cursor.fetchone()
        payment_id = pay_row[0]
        created_at = pay_row[1]

        # 4. Determine and update new invoice status atomically
        new_total_paid = existing_paid + amount_paid
        new_remaining_balance = total_amount - new_total_paid

        if new_remaining_balance == Decimal("0.00"):
            new_status = "Paid"
        else:
            new_status = "Partially Paid"

        cursor.execute(
            '''
            UPDATE public."SupplierInvoices"
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = %s;
            ''',
            (new_status, invoice_id)
        )

        # 5. Record Audit Log inside the transaction
        log_audit_event(
            action="PAYMENT_RECORDED",
            table_name="SupplierPayments",
            record_id=payment_id,
            user_id=int(user_id),
            cursor=cursor
        )

        conn.commit()

        # Non-blocking consolidated payment notification dispatch to Supplier
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_supplier_user_id
            )
            supplier_user_id = get_supplier_user_id(supplier_id)
            if supplier_user_id:
                if new_status == "Paid":
                    title = "Payment Received — Invoice Settled"
                    msg = (
                        f"Final payment of ₹{amount_paid:.2f} recorded for invoice {invoice_number} "
                        f"(Ref: {payment_reference}). Remaining balance: ₹{new_remaining_balance:.2f}. "
                        f"Invoice status is now Fully Paid."
                    )
                else:
                    title = "Payment Received"
                    msg = (
                        f"Payment of ₹{amount_paid:.2f} recorded for invoice {invoice_number} "
                        f"(Ref: {payment_reference}). Remaining balance: ₹{new_remaining_balance:.2f}. "
                        f"Invoice status is now Partially Paid."
                    )

                create_notification(
                    user_id=supplier_user_id,
                    title=title,
                    message=msg,
                    notification_type="Payment",
                    priority="Normal",
                    reference_type="Payment",
                    reference_id=payment_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to dispatch payment notification: {notif_err}", flush=True)

        result = {
            "payment": {
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "supplier_id": supplier_id,
                "payment_date": _format_date(parsed_payment_date),
                "amount_paid": _format_decimal(amount_paid),
                "payment_method": payment_method,
                "payment_reference": payment_reference,
                "notes": notes,
                "recorded_by": int(user_id),
                "created_at": _format_date(created_at)
            },
            "invoice": {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "total_amount": _format_decimal(total_amount),
                "total_paid": _format_decimal(new_total_paid),
                "remaining_balance": _format_decimal(new_remaining_balance),
                "status": new_status
            }
        }

        return result, None, 201

    except Error as db_err:
        if conn:
            conn.rollback()
        return None, f"Database error recording payment: {str(db_err)}", 500
    except Exception as ex:
        if conn:
            conn.rollback()
        return None, f"Unexpected error recording payment: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_payments(user_id, role, supplier_id_filter=None, invoice_id_filter=None,
                 payment_method_filter=None, date_from=None, date_to=None,
                 search=None, page=1, limit=50):
    """
    List supplier payment records with role-based access control and supplier isolation.
    - Owner/Manager: Full organization-wide visibility with optional filters.
    - Supplier: Strictly isolated to payments disbursed to their supplier profile.
    - Employee: Access denied (403).
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. You do not have permission to view financial payment records.", 403

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Enforce Supplier Isolation
        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return {"payments": [], "stats": {"total_payments": 0, "total_disbursed": 0.0}, "total_count": 0}, None, 200
            target_supplier_id = auth_supplier_id
        else:
            try:
                target_supplier_id = int(supplier_id_filter) if supplier_id_filter else None
            except (ValueError, TypeError):
                target_supplier_id = None

        query = '''
            SELECT 
                sp.payment_id,
                sp.invoice_id,
                si.invoice_number,
                si.total_amount AS invoice_total,
                si.status AS invoice_status,
                sp.supplier_id,
                s.supplier_name,
                sp.payment_date,
                sp.amount_paid,
                sp.payment_method,
                sp.payment_reference,
                sp.notes,
                sp.recorded_by,
                u.username AS recorded_by_name,
                sp.created_at
            FROM public."SupplierPayments" sp
            JOIN public."SupplierInvoices" si ON sp.invoice_id = si.invoice_id
            JOIN public."Suppliers" s ON sp.supplier_id = s.supplier_id
            JOIN public."Users" u ON sp.recorded_by = u.user_id
            WHERE 1=1
        '''
        params = []

        if target_supplier_id is not None:
            query += ' AND sp.supplier_id = %s'
            params.append(target_supplier_id)

        if invoice_id_filter:
            try:
                query += ' AND sp.invoice_id = %s'
                params.append(int(invoice_id_filter))
            except (ValueError, TypeError):
                pass

        if payment_method_filter:
            query += ' AND sp.payment_method = %s'
            params.append(str(payment_method_filter).strip())

        if date_from:
            query += ' AND sp.payment_date >= %s'
            params.append(str(date_from).split("T")[0])

        if date_to:
            query += ' AND sp.payment_date <= %s'
            params.append(str(date_to).split("T")[0])

        if search:
            search_param = f"%{str(search).strip()}%"
            query += ' AND (si.invoice_number ILIKE %s OR sp.payment_reference ILIKE %s OR s.supplier_name ILIKE %s)'
            params.extend([search_param, search_param, search_param])

        query += ' ORDER BY sp.payment_date DESC, sp.created_at DESC'

        cursor.execute(query, tuple(params))
        all_rows = cursor.fetchall()
        total_count = len(all_rows)

        # Pagination
        try:
            page = max(1, int(page))
            limit = max(1, min(200, int(limit)))
        except (ValueError, TypeError):
            page = 1
            limit = 50

        offset = (page - 1) * limit
        paged_rows = all_rows[offset : offset + limit]

        total_disbursed = Decimal("0.00")
        method_counts = {}

        for r in all_rows:
            p_amt = Decimal(str(r[8]))
            total_disbursed += p_amt
            pm = r[9]
            method_counts[pm] = method_counts.get(pm, 0) + 1

        payments_list = []
        for r in paged_rows:
            payments_list.append({
                "payment_id": r[0],
                "invoice_id": r[1],
                "invoice_number": r[2],
                "invoice_total": _format_decimal(r[3]),
                "invoice_status": r[4],
                "supplier_id": r[5],
                "supplier_name": r[6],
                "payment_date": _format_date(r[7]),
                "amount_paid": _format_decimal(r[8]),
                "payment_method": r[9],
                "payment_reference": r[10],
                "notes": r[11],
                "recorded_by": r[12],
                "recorded_by_name": r[13],
                "created_at": _format_date(r[14])
            })

        stats = {
            "total_payments": total_count,
            "total_disbursed": _format_decimal(total_disbursed),
            "method_counts": method_counts,
            "page": page,
            "limit": limit
        }

        return {"payments": payments_list, "stats": stats, "total_count": total_count}, None, 200

    except Error as db_err:
        return None, f"Database error listing payments: {str(db_err)}", 500
    except Exception as ex:
        return None, f"Unexpected error listing payments: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_payment_by_id(payment_id, user_id, role):
    """
    Retrieve single payment record with linked invoice details.
    - Owner/Manager: Full access.
    - Supplier: Strictly isolated to own supplier profile.
    - Employee: Access denied (403).
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. You do not have permission to view payment records.", 403

    try:
        p_id = int(payment_id)
    except (ValueError, TypeError):
        return None, "Invalid payment_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return None, "Access denied. User not linked to a supplier profile", 403
        else:
            auth_supplier_id = None

        cursor.execute(
            '''
            SELECT 
                sp.payment_id,
                sp.invoice_id,
                si.invoice_number,
                si.total_amount AS invoice_total,
                si.status AS invoice_status,
                sp.supplier_id,
                s.supplier_name,
                sp.payment_date,
                sp.amount_paid,
                sp.payment_method,
                sp.payment_reference,
                sp.notes,
                sp.recorded_by,
                u.username AS recorded_by_name,
                sp.created_at
            FROM public."SupplierPayments" sp
            JOIN public."SupplierInvoices" si ON sp.invoice_id = si.invoice_id
            JOIN public."Suppliers" s ON sp.supplier_id = s.supplier_id
            JOIN public."Users" u ON sp.recorded_by = u.user_id
            WHERE sp.payment_id = %s;
            ''',
            (p_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Payment record not found", 404

        pay_supplier_id = row[5]
        if role == "Supplier" and pay_supplier_id != auth_supplier_id:
            return None, "Access denied. Payment belongs to another supplier", 403

        payment_data = {
            "payment_id": row[0],
            "invoice_id": row[1],
            "invoice_number": row[2],
            "invoice_total": _format_decimal(row[3]),
            "invoice_status": row[4],
            "supplier_id": row[5],
            "supplier_name": row[6],
            "payment_date": _format_date(row[7]),
            "amount_paid": _format_decimal(row[8]),
            "payment_method": row[9],
            "payment_reference": row[10],
            "notes": row[11],
            "recorded_by": row[12],
            "recorded_by_name": row[13],
            "created_at": _format_date(row[14])
        }

        return {"payment": payment_data}, None, 200

    except Error as db_err:
        return None, f"Database error retrieving payment: {str(db_err)}", 500
    except Exception as ex:
        return None, f"Unexpected error retrieving payment: {str(ex)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
