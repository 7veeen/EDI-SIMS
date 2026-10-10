from psycopg2 import Error
from decimal import Decimal
from datetime import datetime
from app.extensions import get_db_connection


def get_inventory(search=None, status_filter=None, category_id=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                i.inventory_id,
                i.product_id,
                p.product_name,
                p.sku,
                c.category_id,
                c.category_name,
                i.quantity_available,
                p.reorder_level,
                p.status AS product_status,
                p.selling_price,
                i.last_updated
            FROM public."Inventory" i
            JOIN public."Products" p ON i.product_id = p.product_id
            JOIN public."Categories" c ON p.category_id = c.category_id
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.product_name ILIKE %s OR p.sku ILIKE %s)'
            params.extend([f"%{search}%", f"%{search}%"])

        if category_id:
            query += ' AND p.category_id = %s'
            params.append(category_id)

        if status_filter:
            norm_filter = str(status_filter).lower().strip()
            if norm_filter in ['low_stock', 'low']:
                query += ' AND (i.quantity_available > 0 AND i.quantity_available <= p.reorder_level)'
            elif norm_filter in ['out_of_stock', 'out']:
                query += ' AND (i.quantity_available <= 0)'
            elif norm_filter in ['in_stock', 'in']:
                query += ' AND (i.quantity_available > p.reorder_level)'

        query += ' ORDER BY p.product_name ASC'

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        items = []
        in_stock_count = 0
        low_stock_count = 0
        out_of_stock_count = 0
        total_quantity = 0

        for r in rows:
            qty = r[6]
            reorder = r[7]
            total_quantity += qty

            if qty <= 0:
                stock_status = "Out of Stock"
                out_of_stock_count += 1
            elif qty <= reorder:
                stock_status = "Low Stock"
                low_stock_count += 1
            else:
                stock_status = "In Stock"
                in_stock_count += 1

            price_val = float(r[9]) if isinstance(r[9], Decimal) else float(r[9] or 0)
            last_up = r[10].isoformat() if isinstance(r[10], datetime) else str(r[10])

            items.append({
                "inventory_id": r[0],
                "product_id": r[1],
                "product_name": r[2],
                "sku": r[3],
                "category_id": r[4],
                "category_name": r[5],
                "quantity_available": qty,
                "reorder_level": reorder,
                "stock_status": stock_status,
                "product_status": r[8],
                "selling_price": price_val,
                "last_updated": last_up
            })

        stats = {
            "total_items": len(items),
            "in_stock": in_stock_count,
            "low_stock": low_stock_count,
            "out_of_stock": out_of_stock_count,
            "total_quantity": total_quantity
        }

        return {"inventory": items, "stats": stats}, None

    except Error as e:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_inventory_by_id(inventory_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                i.inventory_id,
                i.product_id,
                p.product_name,
                p.sku,
                c.category_id,
                c.category_name,
                i.quantity_available,
                p.reorder_level,
                p.status AS product_status,
                p.selling_price,
                i.last_updated
            FROM public."Inventory" i
            JOIN public."Products" p ON i.product_id = p.product_id
            JOIN public."Categories" c ON p.category_id = c.category_id
            WHERE i.inventory_id = %s
        '''
        cursor.execute(query, (inventory_id,))
        r = cursor.fetchone()

        if r is None:
            return None, "Inventory record not found"

        qty = r[6]
        reorder = r[7]
        if qty <= 0:
            stock_status = "Out of Stock"
        elif qty <= reorder:
            stock_status = "Low Stock"
        else:
            stock_status = "In Stock"

        price_val = float(r[9]) if isinstance(r[9], Decimal) else float(r[9] or 0)
        last_up = r[10].isoformat() if isinstance(r[10], datetime) else str(r[10])

        item = {
            "inventory_id": r[0],
            "product_id": r[1],
            "product_name": r[2],
            "sku": r[3],
            "category_id": r[4],
            "category_name": r[5],
            "quantity_available": qty,
            "reorder_level": reorder,
            "stock_status": stock_status,
            "product_status": r[8],
            "selling_price": price_val,
            "last_updated": last_up
        }

        return item, None

    except Error:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def adjust_inventory(inventory_id, new_quantity, user_id=None, notes=None):
    conn = None
    cursor = None

    try:
        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                return None, "Inventory quantity cannot be negative"
        except (ValueError, TypeError):
            return None, "Invalid quantity provided"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Lock and read current inventory record
        cursor.execute(
            '''
            SELECT i.inventory_id, i.product_id, i.quantity_available, p.product_name, p.reorder_level
            FROM public."Inventory" i
            JOIN public."Products" p ON i.product_id = p.product_id
            WHERE i.inventory_id = %s
            FOR UPDATE
            ''',
            (inventory_id,)
        )
        existing = cursor.fetchone()
        if existing is None:
            return None, "Inventory record not found"

        product_id = existing[1]
        old_quantity = existing[2]
        product_name = existing[3]
        reorder_level = existing[4]
        delta = new_quantity - old_quantity

        # Update inventory quantity
        cursor.execute(
            '''
            UPDATE public."Inventory"
            SET quantity_available = %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE inventory_id = %s
            RETURNING inventory_id, product_id, quantity_available, last_updated
            ''',
            (new_quantity, inventory_id)
        )
        updated_row = cursor.fetchone()

        # Record in StockTransactions to preserve transaction history
        transaction_id = None
        if delta != 0 and user_id:
            transaction_type = "STOCK_IN" if delta > 0 else "STOCK_OUT"
            transaction_qty = abs(delta)

            cursor.execute(
                '''
                INSERT INTO public."StockTransactions"
                (product_id, user_id, transaction_type, quantity, transaction_date)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING transaction_id
                ''',
                (product_id, user_id, transaction_type, transaction_qty)
            )
            tx_row = cursor.fetchone()
            if tx_row:
                transaction_id = tx_row[0]

        conn.commit()

        # Trigger Event I: Low Stock Alert if reduced to or below reorder level
        if delta < 0 and new_quantity <= reorder_level:
            try:
                from app.services.team3.notification_service import (
                    create_notification,
                    get_active_managers_and_owners
                )
                mgr_owner_ids = get_active_managers_and_owners()
                for mo_id in mgr_owner_ids:
                    create_notification(
                        user_id=mo_id,
                        title="Low Stock Alert",
                        message=f"Product {product_name} is low in stock. Current quantity: {new_quantity}.",
                        notification_type="Low Stock",
                        priority="High",
                        reference_type="Product",
                        reference_id=product_id
                    )
            except Exception as notif_err:
                print(f"[NOTIFICATION WARNING] Failed to send low stock notification in adjust_inventory: {notif_err}", flush=True)

        stock_status = "Out of Stock" if new_quantity <= 0 else ("Low Stock" if new_quantity <= reorder_level else "In Stock")

        result = {
            "inventory_id": updated_row[0],
            "product_id": updated_row[1],
            "product_name": product_name,
            "previous_quantity": old_quantity,
            "quantity_available": updated_row[2],
            "delta": delta,
            "stock_status": stock_status,
            "last_updated": updated_row[3].isoformat() if isinstance(updated_row[3], datetime) else str(updated_row[3]),
            "transaction_id": transaction_id
        }

        return result, None

    except Error as e:
        if conn:
            conn.rollback()
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def stock_in(shipment_id, product_id, quantity, notes=None, user_id=None, role=None, username=None):
    """
    Perform goods receipt / Stock-In for a Delivered shipment.
    Atomically updates Inventory and inserts exactly one StockTransactions record.
    Strictly verifies employee assignment, shipment status, product eligibility, and receivable limits.
    """
    if role == 'Supplier':
        return None, "Access denied. Suppliers cannot perform stock-in operations."
    if role not in ('Owner', 'Manager', 'Employee'):
        return None, "Access denied. You do not have permission to perform this action."

    # Validate shipment_id
    if shipment_id is None or shipment_id == "":
        return None, "shipment_id is required"
    try:
        shipment_id = int(shipment_id)
    except (ValueError, TypeError):
        return None, "shipment_id must be an integer"

    # Validate product_id
    if product_id is None or product_id == "":
        return None, "product_id is required"
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return None, "product_id must be an integer"

    # Validate quantity
    if quantity is None or quantity == "":
        return None, "quantity is required"
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return None, "quantity must be an integer"
    if quantity <= 0:
        return None, "quantity must be greater than zero"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Fetch Shipment
        cursor.execute("""
            SELECT shipment_id, shipment_number, purchase_order_id, supplier_id, status, assigned_employee_id, COALESCE(receiving_status, 'Pending Receipt')
            FROM "Shipments"
            WHERE shipment_id = %s
        """, (shipment_id,))
        shp = cursor.fetchone()
        if not shp:
            conn.rollback()
            return None, "Shipment not found"

        shipment_num = shp[1]
        po_id = shp[2]
        supplier_id = shp[3]
        shp_status = shp[4] or ""
        assigned_emp_id = shp[5]
        rec_status = shp[6]

        # Role-based assignment check: Employees can only Stock-In shipments assigned to them
        if role == 'Employee':
            if not assigned_emp_id or assigned_emp_id != int(user_id):
                conn.rollback()
                return None, "Access denied. You can only perform stock-in on shipments assigned to you."

        # Shipment must be Delivered before receiving stock
        if shp_status.lower() != 'delivered':
            conn.rollback()
            return None, f"Shipment status must be 'Delivered' before receiving stock. Current status: '{shp_status}'"

        # 2. Fetch Product
        cursor.execute("""
            SELECT product_id, product_name, sku, reorder_level
            FROM "Products"
            WHERE product_id = %s
        """, (product_id,))
        prod = cursor.fetchone()
        if not prod:
            conn.rollback()
            return None, "Product not found"

        prod_name = prod[1]
        prod_sku = prod[2] or ""
        reorder_level = prod[3] or 10

        # 3. Verify product belongs to the shipment's PO
        cursor.execute("""
            SELECT quantity FROM "PurchaseOrderItems"
            WHERE purchase_order_id = %s AND product_id = %s
        """, (po_id, product_id))
        poi_row = cursor.fetchone()
        if not poi_row:
            conn.rollback()
            return None, "Product does not belong to this shipment's purchase order"

        poi_qty = poi_row[0]

        # Check approved quotation for exact approved quantity
        cursor.execute("""
            SELECT quantity FROM "SupplierQuotations"
            WHERE purchase_order_id = %s AND product_id = %s AND status IN ('Approved', 'Accepted')
            LIMIT 1
        """, (po_id, product_id))
        quote_row = cursor.fetchone()
        expected_qty = quote_row[0] if quote_row else poi_qty

        # 4. Check already received quantity for this shipment and product
        cursor.execute("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE shipment_id = %s AND product_id = %s AND transaction_type = 'STOCK_IN'
        """, (shipment_id, product_id))
        already_received = cursor.fetchone()[0]

        remaining_receivable = max(0, expected_qty - already_received)

        if remaining_receivable <= 0:
            conn.rollback()
            return None, f"Product '{prod_name}' has already been fully received for this shipment"

        if quantity > remaining_receivable:
            conn.rollback()
            return None, f"Received quantity ({quantity}) exceeds remaining receivable quantity ({remaining_receivable})"

        # 5. Atomic Update: Inventory quantity_available
        cursor.execute("""
            SELECT inventory_id, quantity_available
            FROM "Inventory"
            WHERE product_id = %s
            FOR UPDATE
        """, (product_id,))
        inv_row = cursor.fetchone()

        if inv_row:
            inv_id = inv_row[0]
            old_qty = inv_row[1]
            new_qty = old_qty + quantity
            cursor.execute("""
                UPDATE "Inventory"
                SET quantity_available = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE inventory_id = %s
            """, (new_qty, inv_id))
        else:
            old_qty = 0
            new_qty = quantity
            cursor.execute("""
                INSERT INTO "Inventory" (product_id, quantity_available, last_updated)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                RETURNING inventory_id
            """, (product_id, new_qty))
            inv_id = cursor.fetchone()[0]

        # 6. Atomic Insert: StockTransactions
        tx_notes = notes.strip() if notes else f"Received from shipment {shipment_num}"
        cursor.execute("""
            INSERT INTO "StockTransactions" (
                product_id,
                user_id,
                purchase_order_id,
                shipment_id,
                transaction_type,
                quantity,
                transaction_date,
                notes
            )
            VALUES (%s, %s, %s, %s, 'STOCK_IN', %s, CURRENT_TIMESTAMP, %s)
            RETURNING transaction_id, transaction_date
        """, (
            product_id,
            int(user_id) if user_id else None,
            po_id,
            shipment_id,
            quantity,
            tx_notes
        ))
        tx_row = cursor.fetchone()
        tx_id = tx_row[0]
        tx_date = tx_row[1]

        # 7. Check overall shipment receiving progress and update Shipments.receiving_status
        cursor.execute("""
            SELECT poi.product_id, poi.quantity
            FROM "PurchaseOrderItems" poi
            WHERE poi.purchase_order_id = %s
        """, (po_id,))
        all_poi = cursor.fetchall()

        all_items_fully_received = True
        total_exp_all = 0
        total_rec_all = 0

        for it in all_poi:
            it_pid = it[0]
            it_poi_qty = it[1]

            cursor.execute("""
                SELECT quantity FROM "SupplierQuotations"
                WHERE purchase_order_id = %s AND product_id = %s AND status IN ('Approved', 'Accepted')
                LIMIT 1
            """, (po_id, it_pid))
            it_q = cursor.fetchone()
            it_exp = it_q[0] if it_q else it_poi_qty

            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM "StockTransactions"
                WHERE shipment_id = %s AND product_id = %s AND transaction_type = 'STOCK_IN'
            """, (shipment_id, it_pid))
            it_rec = cursor.fetchone()[0]

            total_exp_all += it_exp
            total_rec_all += it_rec
            if it_rec < it_exp:
                all_items_fully_received = False

        if all_items_fully_received:
            new_rec_status = "Fully Received"
        elif total_rec_all > 0:
            new_rec_status = "Partially Received"
        else:
            new_rec_status = "Pending Receipt"

        cursor.execute("""
            UPDATE "Shipments"
            SET receiving_status = %s,
                updated_at = NOW()
            WHERE shipment_id = %s
        """, (new_rec_status, shipment_id))

        # 8. Record in OrderStatusHistory
        history_note = f"Received {quantity} units of {prod_name} (SKU: {prod_sku}). Notes: {tx_notes}"
        cursor.execute("""
            INSERT INTO "OrderStatusHistory" (
                purchase_order_id,
                shipment_id,
                supplier_id,
                status,
                previous_status,
                action,
                location,
                notes,
                changed_by,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, 'STOCK_IN', 'Inventory Receiving Bay', %s, %s, NOW())
        """, (
            po_id,
            shipment_id,
            supplier_id,
            shp_status,
            shp_status,
            history_note,
            username or role or "Employee"
        ))

        conn.commit()

        # Trigger Event J: Stock-In Completed -> notify relevant Managers/Owners (excluding the actor)
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_active_managers_and_owners,
                get_po_creator_user_id
            )
            actor_uid = int(user_id) if user_id else None
            recipients = set(get_active_managers_and_owners(exclude_user_id=actor_uid))
            if po_id:
                po_creator = get_po_creator_user_id(po_id)
                if po_creator and po_creator != actor_uid:
                    recipients.add(po_creator)

            for r_uid in recipients:
                create_notification(
                    user_id=r_uid,
                    title="Stock Received",
                    message=f"Stock-In completed for shipment #{shipment_id}.",
                    notification_type="Stock-In",
                    priority="Normal",
                    reference_type="Shipment",
                    reference_id=shipment_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to send stock-in notification: {notif_err}", flush=True)

        stock_status = "Out of Stock" if new_qty <= 0 else ("Low Stock" if new_qty <= reorder_level else "In Stock")

        return {
            "message": "Stock-in completed successfully",
            "transaction": {
                "transaction_id": tx_id,
                "product_id": product_id,
                "product_name": prod_name,
                "sku": prod_sku,
                "transaction_type": "STOCK_IN",
                "quantity": quantity,
                "shipment_id": shipment_id,
                "shipment_number": shipment_num,
                "purchase_order_id": po_id,
                "notes": tx_notes,
                "transaction_date": tx_date.isoformat() if tx_date else datetime.now().isoformat()
            },
            "inventory": {
                "inventory_id": inv_id,
                "product_id": product_id,
                "product_name": prod_name,
                "previous_quantity": old_qty,
                "quantity_available": new_qty,
                "delta": quantity,
                "stock_status": stock_status
            },
            "receiving_progress": {
                "expected_quantity": expected_qty,
                "already_received": already_received + quantity,
                "remaining_quantity": remaining_receivable - quantity,
                "receiving_status": new_rec_status
            }
        }, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def stock_out(product_id, quantity, reason=None, notes=None, user_id=None, role=None, username=None):
    """
    Perform stock reduction / Stock-Out.
    Atomically decreases Inventory and inserts exactly one StockTransactions record.
    Prevents negative inventory, validates role authorization, and triggers low-stock alerts.
    """
    if role == 'Supplier':
        return None, "Access denied. Suppliers cannot perform stock-out operations."
    if role not in ('Owner', 'Manager', 'Employee'):
        return None, "Access denied. You do not have permission to perform this action."

    # Validate product_id
    if product_id is None or product_id == "":
        return None, "product_id is required"
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return None, "product_id must be an integer"

    # Validate quantity
    if quantity is None or quantity == "":
        return None, "quantity is required"
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return None, "quantity must be an integer"
    if quantity <= 0:
        return None, "quantity must be greater than zero"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Fetch Product
        cursor.execute("""
            SELECT product_id, product_name, sku, reorder_level
            FROM "Products"
            WHERE product_id = %s
        """, (product_id,))
        prod = cursor.fetchone()
        if not prod:
            conn.rollback()
            return None, "Product not found"

        prod_name = prod[1]
        prod_sku = prod[2] or ""
        reorder_level = prod[3] or 10

        # 2. Lock and check Inventory
        cursor.execute("""
            SELECT inventory_id, quantity_available
            FROM "Inventory"
            WHERE product_id = %s
            FOR UPDATE
        """, (product_id,))
        inv_row = cursor.fetchone()
        if not inv_row:
            conn.rollback()
            return None, "Inventory record not found for this product"

        inv_id = inv_row[0]
        current_stock = inv_row[1]

        if quantity > current_stock:
            conn.rollback()
            return None, f"Stock-Out quantity ({quantity}) exceeds available stock ({current_stock}). Inventory cannot become negative."

        new_stock = current_stock - quantity

        # 3. Update Inventory
        cursor.execute("""
            UPDATE "Inventory"
            SET quantity_available = %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE inventory_id = %s
        """, (new_stock, inv_id))

        # 4. Insert StockTransactions
        combined_notes = ""
        if reason and notes:
            combined_notes = f"Reason: {reason}. Notes: {notes}"
        elif reason:
            combined_notes = f"Reason: {reason}"
        elif notes:
            combined_notes = str(notes)
        else:
            combined_notes = "Stock-out issued"

        cursor.execute("""
            INSERT INTO "StockTransactions" (
                product_id,
                user_id,
                transaction_type,
                quantity,
                transaction_date,
                notes
            )
            VALUES (%s, %s, 'STOCK_OUT', %s, CURRENT_TIMESTAMP, %s)
            RETURNING transaction_id, transaction_date
        """, (
            product_id,
            int(user_id) if user_id else None,
            quantity,
            combined_notes
        ))
        tx_row = cursor.fetchone()
        tx_id = tx_row[0]
        tx_date = tx_row[1]

        conn.commit()

        # Trigger Event I: Low Stock Alert -> notify active Managers and Owners
        if new_stock <= reorder_level:
            try:
                from app.services.team3.notification_service import (
                    create_notification,
                    get_active_managers_and_owners
                )
                mgr_owner_ids = get_active_managers_and_owners()
                for mo_id in mgr_owner_ids:
                    create_notification(
                        user_id=mo_id,
                        title="Low Stock Alert",
                        message=f"Product {prod_name} is low in stock. Current quantity: {new_stock}.",
                        notification_type="Low Stock",
                        priority="High",
                        reference_type="Product",
                        reference_id=product_id
                    )
            except Exception as notif_err:
                print(f"[NOTIFICATION WARNING] Failed to send low stock notification in stock_out: {notif_err}", flush=True)

        stock_status = "Out of Stock" if new_stock <= 0 else ("Low Stock" if new_stock <= reorder_level else "In Stock")

        return {
            "message": "Stock-out completed successfully",
            "transaction": {
                "transaction_id": tx_id,
                "product_id": product_id,
                "product_name": prod_name,
                "sku": prod_sku,
                "transaction_type": "STOCK_OUT",
                "quantity": quantity,
                "notes": combined_notes,
                "transaction_date": tx_date.isoformat() if tx_date else datetime.now().isoformat()
            },
            "inventory": {
                "inventory_id": inv_id,
                "product_id": product_id,
                "product_name": prod_name,
                "previous_quantity": current_stock,
                "quantity_available": new_stock,
                "delta": -quantity,
                "stock_status": stock_status
            }
        }, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_stock_transactions(product_id=None, transaction_type=None, date_from=None, date_to=None, user_id_filter=None, shipment_id_filter=None, role=None):
    """
    Retrieve stock movement transaction history with flexible filters.
    Available to Owner, Manager, Employee. Suppliers are forbidden.
    """
    if role == 'Supplier':
        return None, "Access denied. Suppliers cannot view transaction history."

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                st.transaction_id,
                st.product_id,
                p.product_name,
                p.sku,
                st.user_id,
                u.username,
                r.role_name AS user_role,
                st.purchase_order_id,
                st.shipment_id,
                shp.shipment_number,
                st.transaction_type,
                st.quantity,
                st.transaction_date,
                st.notes
            FROM "StockTransactions" st
            JOIN "Products" p ON st.product_id = p.product_id
            LEFT JOIN "Users" u ON st.user_id = u.user_id
            LEFT JOIN "Roles" r ON u.role_id = r.role_id
            LEFT JOIN "Shipments" shp ON st.shipment_id = shp.shipment_id
            WHERE 1=1
        """
        params = []

        if product_id:
            try:
                query += " AND st.product_id = %s"
                params.append(int(product_id))
            except (ValueError, TypeError):
                pass

        if transaction_type and transaction_type.strip():
            query += " AND st.transaction_type = %s"
            params.append(transaction_type.strip().upper())

        if user_id_filter:
            try:
                query += " AND st.user_id = %s"
                params.append(int(user_id_filter))
            except (ValueError, TypeError):
                pass

        if shipment_id_filter:
            try:
                query += " AND st.shipment_id = %s"
                params.append(int(shipment_id_filter))
            except (ValueError, TypeError):
                pass

        if date_from and date_from.strip():
            query += " AND st.transaction_date >= %s"
            params.append(date_from.strip())

        if date_to and date_to.strip():
            query += " AND st.transaction_date <= %s"
            params.append(date_to.strip() + " 23:59:59" if len(date_to.strip()) == 10 else date_to.strip())

        query += " ORDER BY st.transaction_id DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        transactions = []
        for r in rows:
            tx_d = r[12]
            transactions.append({
                "transaction_id": r[0],
                "product_id": r[1],
                "product_name": r[2],
                "sku": r[3] or "",
                "user_id": r[4],
                "username": r[5] or "System",
                "user_role": r[6] or "",
                "purchase_order_id": r[7],
                "shipment_id": r[8],
                "shipment_number": r[9] or "",
                "transaction_type": r[10],
                "quantity": r[11],
                "transaction_date": tx_d.isoformat() if isinstance(tx_d, datetime) else str(tx_d),
                "notes": r[13] or ""
            })

        return transactions, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_stock_transaction_by_id(transaction_id, role=None):
    """
    Get a single stock transaction record by ID.
    """
    if role == 'Supplier':
        return None, "Access denied. Suppliers cannot view transaction history."

    try:
        transaction_id = int(transaction_id)
    except (ValueError, TypeError):
        return None, "Invalid transaction_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                st.transaction_id,
                st.product_id,
                p.product_name,
                p.sku,
                st.user_id,
                u.username,
                r.role_name AS user_role,
                st.purchase_order_id,
                st.shipment_id,
                shp.shipment_number,
                st.transaction_type,
                st.quantity,
                st.transaction_date,
                st.notes
            FROM "StockTransactions" st
            JOIN "Products" p ON st.product_id = p.product_id
            LEFT JOIN "Users" u ON st.user_id = u.user_id
            LEFT JOIN "Roles" r ON u.role_id = r.role_id
            LEFT JOIN "Shipments" shp ON st.shipment_id = shp.shipment_id
            WHERE st.transaction_id = %s
        """
        cursor.execute(query, (transaction_id,))
        r = cursor.fetchone()

        if not r:
            return None, "Transaction not found"

        tx_d = r[12]
        tx = {
            "transaction_id": r[0],
            "product_id": r[1],
            "product_name": r[2],
            "sku": r[3] or "",
            "user_id": r[4],
            "username": r[5] or "System",
            "user_role": r[6] or "",
            "purchase_order_id": r[7],
            "shipment_id": r[8],
            "shipment_number": r[9] or "",
            "transaction_type": r[10],
            "quantity": r[11],
            "transaction_date": tx_d.isoformat() if isinstance(tx_d, datetime) else str(tx_d),
            "notes": r[13] or ""
        }

        return tx, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

