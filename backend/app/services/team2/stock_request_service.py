from datetime import datetime, date
from app.extensions import get_db_connection


def resolve_supplier_id_for_user(cursor, user_id):
    """Resolve the supplier_id for an authenticated user with role Supplier."""
    cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
    row = cursor.fetchone()
    return row[0] if row else None


def get_stock_requests(user_id=None, role=None, status=None, priority=None, search=None, supplier_id=None):
    """
    Get list of stock requests with strict role-based access and supplier isolation.
    - Owner / Manager: can view all requests or filter by supplier_id.
    - Supplier: can ONLY view requests assigned to their supplier profile.
    - Employee: access denied.
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. Only Owners, Managers, and Suppliers can view stock requests."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Enforce Supplier Isolation
        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id:
                return [], None
            filter_supplier_id = auth_supplier_id
        else:
            filter_supplier_id = int(supplier_id) if supplier_id else None

        query = """
            SELECT
                sr.stock_request_id,
                sr.request_number,
                sr.requested_by,
                u.username AS requested_by_name,
                sr.supplier_id,
                s.supplier_name,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                sr.status,
                sr.priority,
                sr.required_date,
                sr.notes,
                sr.supplier_response_notes,
                sr.responded_at,
                sr.created_at,
                sr.updated_at,
                COALESCE(COUNT(sri.stock_request_item_id), 0) AS items_count,
                COALESCE(SUM(sri.requested_quantity), 0) AS total_quantity
            FROM "StockRequests" sr
            JOIN "Suppliers" s ON sr.supplier_id = s.supplier_id
            JOIN "Users" u ON sr.requested_by = u.user_id
            LEFT JOIN "StockRequestItems" sri ON sr.stock_request_id = sri.stock_request_id
            WHERE 1=1
        """
        params = []

        if filter_supplier_id:
            query += " AND sr.supplier_id = %s"
            params.append(filter_supplier_id)

        if status and status.strip() and status != "All Status":
            query += " AND sr.status ILIKE %s"
            params.append(status.strip())

        if priority and priority.strip() and priority != "All Priority":
            query += " AND sr.priority ILIKE %s"
            params.append(priority.strip())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query += """ AND (
                sr.request_number ILIKE %s
                OR s.supplier_name ILIKE %s
                OR sr.notes ILIKE %s
                OR EXISTS (
                    SELECT 1 FROM "StockRequestItems" item
                    JOIN "Products" prod ON item.product_id = prod.product_id
                    WHERE item.stock_request_id = sr.stock_request_id
                    AND (prod.product_name ILIKE %s OR prod.sku ILIKE %s)
                )
            )"""
            params.extend([term, term, term, term, term])

        query += """
            GROUP BY sr.stock_request_id, u.username, s.supplier_name, s.email, s.phone
            ORDER BY sr.created_at DESC
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        results = []
        for r in rows:
            req_id = r[0]
            # Fetch product summary for this request
            cursor.execute("""
                SELECT p.product_name, p.sku, sri.requested_quantity
                FROM "StockRequestItems" sri
                JOIN "Products" p ON sri.product_id = p.product_id
                WHERE sri.stock_request_id = %s
                ORDER BY sri.stock_request_item_id ASC
            """, (req_id,))
            items_raw = cursor.fetchall()
            items_list = []
            for ir in items_raw:
                items_list.append({
                    "product_name": ir[0],
                    "sku": ir[1] or "",
                    "requested_quantity": ir[2]
                })

            primary_product = items_list[0]["product_name"] if items_list else "General Restock"

            results.append({
                "stock_request_id": r[0],
                "request_number": r[1],
                "requested_by": r[2],
                "requested_by_name": r[3] or "Manager",
                "supplier_id": r[4],
                "supplier_name": r[5],
                "supplier_email": r[6] or "",
                "supplier_phone": r[7] or "",
                "status": r[8] or "Pending",
                "priority": r[9] or "Medium",
                "required_date": r[10].isoformat() if r[10] else None,
                "notes": r[11] or "",
                "supplier_response_notes": r[12] or "",
                "responded_at": r[13].isoformat() if r[13] else None,
                "created_at": r[14].isoformat() if r[14] else None,
                "updated_at": r[15].isoformat() if r[15] else None,
                "items_count": int(r[16]),
                "total_quantity": int(r[17]),
                "primary_product": primary_product,
                "items": items_list
            })

        return results, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def get_stock_request_by_id(stock_request_id, user_id=None, role=None):
    """
    Get detailed stock request by ID with strict Supplier Isolation.
    """
    if role not in ("Owner", "Manager", "Supplier"):
        return None, "Access denied. Only Owners, Managers, and Suppliers can view stock requests."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                sr.stock_request_id,
                sr.request_number,
                sr.requested_by,
                u.username AS requested_by_name,
                sr.supplier_id,
                s.supplier_name,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                sr.status,
                sr.priority,
                sr.required_date,
                sr.notes,
                sr.supplier_response_notes,
                sr.responded_at,
                sr.created_at,
                sr.updated_at
            FROM "StockRequests" sr
            JOIN "Suppliers" s ON sr.supplier_id = s.supplier_id
            JOIN "Users" u ON sr.requested_by = u.user_id
            WHERE sr.stock_request_id = %s
        """, (stock_request_id,))
        row = cursor.fetchone()

        if not row:
            return None, "Stock request not found."

        req_supplier_id = row[4]

        # Enforce Supplier Isolation
        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id or auth_supplier_id != req_supplier_id:
                return None, "Access denied. You can only view stock requests assigned to your company."

        # Fetch Line Items
        cursor.execute("""
            SELECT
                sri.stock_request_item_id,
                sri.product_id,
                p.product_name,
                p.sku,
                c.category_name,
                sri.requested_quantity,
                sri.notes,
                p.selling_price
            FROM "StockRequestItems" sri
            JOIN "Products" p ON sri.product_id = p.product_id
            LEFT JOIN "Categories" c ON p.category_id = c.category_id
            WHERE sri.stock_request_id = %s
            ORDER BY sri.stock_request_item_id ASC
        """, (stock_request_id,))
        items_rows = cursor.fetchall()

        items = []
        total_quantity = 0
        for ir in items_rows:
            qty = ir[5]
            total_quantity += qty
            items.append({
                "stock_request_item_id": ir[0],
                "product_id": ir[1],
                "product_name": ir[2],
                "sku": ir[3] or "",
                "category_name": ir[4] or "Uncategorized",
                "requested_quantity": qty,
                "notes": ir[6] or "",
                "reference_price": float(ir[7]) if ir[7] is not None else 0.0
            })

        # Check if quotation exists for this stock request
        cursor.execute("""
            SELECT quotation_id, quotation_number, status, quoted_price, quantity, total_amount, quotation_date
            FROM "SupplierQuotations"
            WHERE stock_request_id = %s
            LIMIT 1
        """, (stock_request_id,))
        q_row = cursor.fetchone()
        quotation_info = None
        if q_row:
            quotation_info = {
                "quotation_id": q_row[0],
                "quotation_number": q_row[1],
                "status": q_row[2],
                "quoted_price": float(q_row[3]) if q_row[3] is not None else 0.0,
                "quantity": q_row[4],
                "total_amount": float(q_row[5]) if q_row[5] is not None else 0.0,
                "quotation_date": q_row[6].isoformat() if q_row[6] else None
            }

        stock_request = {
            "stock_request_id": row[0],
            "request_number": row[1],
            "requested_by": row[2],
            "requested_by_name": row[3] or "Manager",
            "supplier_id": row[4],
            "supplier_name": row[5],
            "supplier_email": row[6] or "",
            "supplier_phone": row[7] or "",
            "status": row[8] or "Pending",
            "priority": row[9] or "Medium",
            "required_date": row[10].isoformat() if row[10] else None,
            "notes": row[11] or "",
            "supplier_response_notes": row[12] or "",
            "responded_at": row[13].isoformat() if row[13] else None,
            "created_at": row[14].isoformat() if row[14] else None,
            "updated_at": row[15].isoformat() if row[15] else None,
            "total_quantity": total_quantity,
            "items_count": len(items),
            "items": items,
            "quotation": quotation_info
        }

        return stock_request, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def create_stock_request(requested_by_user_id, data):
    """
    Create a new stock request.
    Allowed: Owner, Manager
    """
    if not data:
        return None, "Request body is required."

    supplier_id = data.get("supplier_id")
    items = data.get("items")
    priority = data.get("priority", "Medium")
    required_date = data.get("required_date")
    notes = data.get("notes", "").strip() if data.get("notes") else ""

    if not supplier_id:
        return None, "Supplier ID is required."

    if not items or not isinstance(items, list) or len(items) == 0:
        return None, "At least one product item is required."

    if priority not in ("Low", "Medium", "High", "Urgent"):
        priority = "Medium"

    conn = get_db_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # Validate supplier exists
        cursor.execute('SELECT supplier_id, supplier_name FROM "Suppliers" WHERE supplier_id = %s', (int(supplier_id),))
        sup = cursor.fetchone()
        if not sup:
            return None, "Selected supplier does not exist."

        # Validate items
        validated_items = []
        for it in items:
            pid = it.get("product_id")
            qty = it.get("requested_quantity") or it.get("quantity")
            item_notes = it.get("notes", "")

            if not pid:
                return None, "Product ID is required for each item."

            try:
                qty = int(qty)
                if qty <= 0:
                    return None, "Requested quantity must be greater than zero."
            except (ValueError, TypeError):
                return None, "Invalid quantity for product item."

            cursor.execute('SELECT product_id, product_name, sku FROM "Products" WHERE product_id = %s', (int(pid),))
            prod = cursor.fetchone()
            if not prod:
                return None, f"Product ID {pid} does not exist."

            validated_items.append({
                "product_id": int(pid),
                "requested_quantity": qty,
                "notes": item_notes
            })

        # Generate unique request number: SR-YYYY-XXXX
        current_year = datetime.now().year
        cursor.execute("""
            SELECT COALESCE(MAX(stock_request_id), 0) + 1 FROM "StockRequests"
        """)
        next_id = cursor.fetchone()[0]
        request_number = f"SR-{current_year}-{next_id:04d}"

        # Insert StockRequests header
        cursor.execute("""
            INSERT INTO "StockRequests" (
                request_number,
                requested_by,
                supplier_id,
                status,
                priority,
                required_date,
                notes,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, 'Pending', %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING stock_request_id, created_at
        """, (request_number, int(requested_by_user_id), int(supplier_id), priority, required_date, notes))
        res = cursor.fetchone()
        stock_request_id = res[0]
        created_at = res[1]

        # Insert StockRequestItems
        for it in validated_items:
            cursor.execute("""
                INSERT INTO "StockRequestItems" (
                    stock_request_id,
                    product_id,
                    requested_quantity,
                    notes,
                    created_at
                ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (stock_request_id, it["product_id"], it["requested_quantity"], it["notes"]))

        conn.commit()

        created_request = {
            "stock_request_id": stock_request_id,
            "request_number": request_number,
            "supplier_id": int(supplier_id),
            "supplier_name": sup[1],
            "requested_by": int(requested_by_user_id),
            "status": "Pending",
            "priority": priority,
            "required_date": required_date,
            "notes": notes,
            "items_count": len(validated_items),
            "created_at": created_at.isoformat() if created_at else None
        }

        return created_request, None

    except Exception as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def respond_to_stock_request(stock_request_id, user_id, role, data):
    """
    Supplier response to a Stock Request (Accept or Reject).
    If Supplier Accepts and provides quoted_price, optionally creates a linked SupplierQuotation.
    """
    if role not in ("Supplier", "Owner", "Manager"):
        return None, "Access denied. Only the assigned Supplier or Managers can respond to stock requests."

    if not data:
        return None, "Response data is required."

    action = data.get("action") or data.get("status")
    notes = data.get("notes", "").strip() if data.get("notes") else ""
    quoted_price = data.get("quoted_price")
    valid_until = data.get("valid_until")

    if not action or action not in ("Accept", "Accepted", "Reject", "Rejected", "Quoted"):
        return None, "Action must be 'Accept', 'Reject', or 'Quoted'."

    new_status = "Accepted" if action in ("Accept", "Accepted") else ("Rejected" if action in ("Reject", "Rejected") else "Quoted")

    conn = get_db_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT stock_request_id, request_number, supplier_id, status
            FROM "StockRequests"
            WHERE stock_request_id = %s
            FOR UPDATE
        """, (stock_request_id,))
        sr = cursor.fetchone()

        if not sr:
            return None, "Stock request not found."

        current_status = sr[3]
        req_supplier_id = sr[2]

        if current_status in ("Completed", "Cancelled"):
            return None, f"Cannot respond to a stock request that is {current_status}."

        # Strict Supplier Isolation check
        if role == "Supplier":
            auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
            if not auth_supplier_id or auth_supplier_id != req_supplier_id:
                return None, "Access denied. You can only respond to stock requests assigned to your company."

        # Fetch items for quotation generation if applicable
        cursor.execute("""
            SELECT product_id, requested_quantity
            FROM "StockRequestItems"
            WHERE stock_request_id = %s
        """, (stock_request_id,))
        items = cursor.fetchall()

        created_quotation_id = None
        # If accepted/quoted and quoted_price provided, link a quotation
        if new_status in ("Accepted", "Quoted") and quoted_price is not None:
            try:
                price = float(quoted_price)
                if price <= 0:
                    return None, "Quoted price must be positive."

                # Get quotation number
                year = datetime.now().year
                cursor.execute('SELECT COALESCE(MAX(quotation_id), 0) + 1 FROM "SupplierQuotations"')
                next_q_id = cursor.fetchone()[0]
                q_number = f"QUO-SR{sr[0]:04d}-{next_q_id:03d}"

                primary_item = items[0] if items else (1, 1)
                item_qty = sum(it[1] for it in items) if items else 1
                total_quote_amt = price * item_qty

                cursor.execute("""
                    INSERT INTO "SupplierQuotations" (
                        supplier_id,
                        product_id,
                        quotation_date,
                        quoted_price,
                        quantity,
                        valid_until,
                        status,
                        purchase_order_id,
                        quotation_number,
                        notes,
                        total_amount,
                        submitted_at,
                        stock_request_id
                    ) VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, 'Pending', NULL, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                    RETURNING quotation_id
                """, (
                    req_supplier_id,
                    primary_item[0],
                    price,
                    item_qty,
                    valid_until or (date.today()),
                    q_number,
                    notes or f"Quotation generated from Stock Request {sr[1]}",
                    total_quote_amt,
                    stock_request_id
                ))
                created_quotation_id = cursor.fetchone()[0]
                new_status = "Quoted"

            except (ValueError, TypeError):
                return None, "Invalid quoted price value."

        # Update StockRequests record
        cursor.execute("""
            UPDATE "StockRequests"
            SET status = %s,
                supplier_response_notes = %s,
                responded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE stock_request_id = %s
            RETURNING request_number, status, responded_at
        """, (new_status, notes, stock_request_id))
        upd = cursor.fetchone()

        conn.commit()

        return {
            "message": f"Stock request {upd[0]} updated to '{upd[1]}'.",
            "stock_request_id": stock_request_id,
            "request_number": upd[0],
            "status": upd[1],
            "responded_at": upd[2].isoformat() if upd[2] else None,
            "quotation_id": created_quotation_id
        }, None

    except Exception as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cursor.close()
        conn.close()
