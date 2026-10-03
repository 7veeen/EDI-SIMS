from psycopg2 import Error
from decimal import Decimal
from app.extensions import get_db_connection


def get_products(search=None, category_id=None, status=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                p.category_id,
                c.category_name,
                p.selling_price,
                p.reorder_level,
                p.status,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                i.inventory_id
            FROM public."Products" p
            JOIN public."Categories" c ON p.category_id = c.category_id
            LEFT JOIN public."Inventory" i ON p.product_id = i.product_id
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.product_name ILIKE %s OR p.sku ILIKE %s)'
            params.extend([f"%{search}%", f"%{search}%"])

        if category_id:
            query += ' AND p.category_id = %s'
            params.append(category_id)

        if status:
            query += ' AND p.status = %s'
            params.append(status)

        query += ' ORDER BY p.product_id ASC'

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        products = []
        for r in rows:
            price_val = float(r[5]) if isinstance(r[5], Decimal) else float(r[5] or 0)
            products.append({
                "product_id": r[0],
                "product_name": r[1],
                "sku": r[2],
                "category_id": r[3],
                "category_name": r[4],
                "price": price_val,
                "selling_price": price_val,
                "reorder_level": r[6],
                "status": r[7],
                "quantity_available": r[8],
                "inventory_id": r[9]
            })

        return products, None

    except Error as e:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_product_by_id(product_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                p.category_id,
                c.category_name,
                p.selling_price,
                p.reorder_level,
                p.status,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                i.inventory_id
            FROM public."Products" p
            JOIN public."Categories" c ON p.category_id = c.category_id
            LEFT JOIN public."Inventory" i ON p.product_id = i.product_id
            WHERE p.product_id = %s
        '''
        cursor.execute(query, (product_id,))
        r = cursor.fetchone()

        if r is None:
            return None, "Product not found"

        price_val = float(r[5]) if isinstance(r[5], Decimal) else float(r[5] or 0)
        product = {
            "product_id": r[0],
            "product_name": r[1],
            "sku": r[2],
            "category_id": r[3],
            "category_name": r[4],
            "price": price_val,
            "selling_price": price_val,
            "reorder_level": r[6],
            "status": r[7],
            "quantity_available": r[8],
            "inventory_id": r[9]
        }

        return product, None

    except Error:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_product(product_name, sku, category_id, selling_price, reorder_level=10, initial_stock=0):
    conn = None
    cursor = None

    try:
        # Field validation
        if not product_name or not str(product_name).strip():
            return None, "Product name cannot be empty"

        if not sku or not str(sku).strip():
            return None, "SKU cannot be empty"

        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            return None, "Invalid category ID"

        try:
            selling_price = float(selling_price)
            if selling_price < 0:
                return None, "Selling price must be greater than or equal to 0"
        except (ValueError, TypeError):
            return None, "Selling price must be a valid number"

        try:
            reorder_level = int(reorder_level)
            if reorder_level < 0:
                return None, "Reorder level must be greater than or equal to 0"
        except (ValueError, TypeError):
            return None, "Reorder level must be an integer"

        try:
            initial_stock = int(initial_stock or 0)
            if initial_stock < 0:
                return None, "Initial stock cannot be negative"
        except (ValueError, TypeError):
            return None, "Initial stock must be an integer"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check Category exists
        cursor.execute(
            'SELECT category_id FROM public."Categories" WHERE category_id = %s',
            (category_id,)
        )
        if cursor.fetchone() is None:
            return None, "Category does not exist"

        # Check SKU uniqueness
        cursor.execute(
            'SELECT product_id FROM public."Products" WHERE UPPER(sku) = UPPER(%s)',
            (str(sku).strip(),)
        )
        if cursor.fetchone():
            return None, "Product SKU already exists"

        # Insert Product
        cursor.execute(
            '''
            INSERT INTO public."Products"
            (product_name, category_id, sku, selling_price, reorder_level, status)
            VALUES (%s, %s, %s, %s, %s, 'Active')
            RETURNING product_id, product_name, sku, category_id, selling_price, reorder_level, status
            ''',
            (
                str(product_name).strip(),
                category_id,
                str(sku).strip(),
                selling_price,
                reorder_level
            )
        )
        row = cursor.fetchone()
        new_product_id = row[0]

        # Automatically insert associated Inventory row
        cursor.execute(
            '''
            INSERT INTO public."Inventory"
            (product_id, quantity_available, last_updated)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING inventory_id
            ''',
            (new_product_id, initial_stock)
        )
        inv_row = cursor.fetchone()
        new_inventory_id = inv_row[0]

        conn.commit()

        # Fetch Category Name
        cursor.execute(
            'SELECT category_name FROM public."Categories" WHERE category_id = %s',
            (category_id,)
        )
        cat_name_row = cursor.fetchone()
        category_name = cat_name_row[0] if cat_name_row else ""

        price_val = float(row[4])
        product_dict = {
            "product_id": new_product_id,
            "product_name": row[1],
            "sku": row[2],
            "category_id": row[3],
            "category_name": category_name,
            "price": price_val,
            "selling_price": price_val,
            "reorder_level": row[5],
            "status": row[6],
            "quantity_available": initial_stock,
            "inventory_id": new_inventory_id
        }

        return product_dict, None

    except Error as e:
        if conn:
            conn.rollback()
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_product(product_id, product_name=None, sku=None, category_id=None, selling_price=None, reorder_level=None, status=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify product exists
        cursor.execute(
            'SELECT product_id, product_name, sku, category_id, selling_price, reorder_level, status FROM public."Products" WHERE product_id = %s',
            (product_id,)
        )
        existing = cursor.fetchone()
        if existing is None:
            return None, "Product not found"

        curr_name, curr_sku, curr_cat_id, curr_price, curr_reorder, curr_status = existing[1:]

        # Validate updates
        new_name = str(product_name).strip() if product_name is not None else curr_name
        if not new_name:
            return None, "Product name cannot be empty"

        new_sku = str(sku).strip() if sku is not None else curr_sku
        if not new_sku:
            return None, "SKU cannot be empty"

        if new_sku != curr_sku:
            cursor.execute(
                'SELECT product_id FROM public."Products" WHERE UPPER(sku) = UPPER(%s) AND product_id != %s',
                (new_sku, product_id)
            )
            if cursor.fetchone():
                return None, "Product SKU already in use by another product"

        if category_id is not None:
            try:
                new_cat_id = int(category_id)
                cursor.execute(
                    'SELECT category_id FROM public."Categories" WHERE category_id = %s',
                    (new_cat_id,)
                )
                if cursor.fetchone() is None:
                    return None, "Category does not exist"
            except (ValueError, TypeError):
                return None, "Invalid category ID"
        else:
            new_cat_id = curr_cat_id

        if selling_price is not None:
            try:
                new_price = float(selling_price)
                if new_price < 0:
                    return None, "Selling price must be greater than or equal to 0"
            except (ValueError, TypeError):
                return None, "Selling price must be a valid number"
        else:
            new_price = float(curr_price)

        if reorder_level is not None:
            try:
                new_reorder = int(reorder_level)
                if new_reorder < 0:
                    return None, "Reorder level must be greater than or equal to 0"
            except (ValueError, TypeError):
                return None, "Reorder level must be an integer"
        else:
            new_reorder = curr_reorder

        if status is not None:
            if status not in ["Active", "Inactive"]:
                return None, "Status must be either 'Active' or 'Inactive'"
            new_status = status
        else:
            new_status = curr_status

        cursor.execute(
            '''
            UPDATE public."Products"
            SET product_name = %s,
                sku = %s,
                category_id = %s,
                selling_price = %s,
                reorder_level = %s,
                status = %s
            WHERE product_id = %s
            RETURNING product_id, product_name, sku, category_id, selling_price, reorder_level, status
            ''',
            (new_name, new_sku, new_cat_id, new_price, new_reorder, new_status, product_id)
        )
        row = cursor.fetchone()
        conn.commit()

        # Get Category name and current inventory quantity
        cursor.execute(
            '''
            SELECT c.category_name, COALESCE(i.quantity_available, 0), i.inventory_id
            FROM public."Categories" c
            LEFT JOIN public."Inventory" i ON i.product_id = %s
            WHERE c.category_id = %s
            ''',
            (product_id, new_cat_id)
        )
        extra = cursor.fetchone()
        cat_name = extra[0] if extra else ""
        qty_avail = extra[1] if extra else 0
        inv_id = extra[2] if extra else None

        updated_dict = {
            "product_id": row[0],
            "product_name": row[1],
            "sku": row[2],
            "category_id": row[3],
            "category_name": cat_name,
            "price": float(row[4]),
            "selling_price": float(row[4]),
            "reorder_level": row[5],
            "status": row[6],
            "quantity_available": qty_avail,
            "inventory_id": inv_id
        }

        return updated_dict, None

    except Error:
        if conn:
            conn.rollback()
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_product(product_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check Product exists
        cursor.execute(
            'SELECT product_id, status FROM public."Products" WHERE product_id = %s',
            (product_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return False, "Product not found", None

        # Check if product is referenced in PO items, quotations, or stock transactions
        cursor.execute(
            'SELECT purchase_order_item_id FROM public."PurchaseOrderItems" WHERE product_id = %s LIMIT 1',
            (product_id,)
        )
        has_po = cursor.fetchone() is not None

        cursor.execute(
            'SELECT quotation_id FROM public."SupplierQuotations" WHERE product_id = %s LIMIT 1',
            (product_id,)
        )
        has_quote = cursor.fetchone() is not None

        cursor.execute(
            'SELECT transaction_id FROM public."StockTransactions" WHERE product_id = %s LIMIT 1',
            (product_id,)
        )
        has_transactions = cursor.fetchone() is not None

        if has_po or has_quote or has_transactions:
            # Cannot hard delete due to foreign key integrity constraints.
            # Soft-delete / deactivate product.
            cursor.execute(
                'UPDATE public."Products" SET status = %s WHERE product_id = %s',
                ('Inactive', product_id)
            )
            conn.commit()
            return True, None, "deactivated"

        # If no transactions or orders exist, safe to delete inventory row and product row
        cursor.execute(
            'DELETE FROM public."Inventory" WHERE product_id = %s',
            (product_id,)
        )
        cursor.execute(
            'DELETE FROM public."Products" WHERE product_id = %s',
            (product_id,)
        )
        conn.commit()

        return True, None, "deleted"

    except Error:
        if conn:
            conn.rollback()
        return False, "Database error", None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
