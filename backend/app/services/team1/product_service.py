from psycopg2 import Error

from app.extensions import get_db_connection

def create_product(product_name, sku, category_id, reorder_level, price):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT product_id
            FROM public."Products"
            WHERE sku = %s
            ''',
            (sku,)
        )
        if cursor.fetchone():
            return None, "A product with this SKU already exists"

        cursor.execute(
            '''
            INSERT INTO public."Products"
            (product_name, sku, category_id, reorder_level, selling_price)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING product_id, product_name, sku, category_id, reorder_level, selling_price, status
            ''',
            (product_name, sku, category_id, reorder_level, price)
        )

        new_product = cursor.fetchone()
        product_id = new_product[0]
        
        # Initialize inventory for this product
        cursor.execute(
            '''
            INSERT INTO public."Inventory"
            (product_id, quantity_available)
            VALUES (%s, 0)
            ''',
            (product_id,)
        )
        
        conn.commit()

        return {
            "product_id": new_product[0],
            "product_name": new_product[1],
            "sku": new_product[2],
            "category_id": new_product[3],
            "quantity_available": 0,
            "reorder_level": new_product[4],
            "price": float(new_product[5]),
            "status": new_product[6]
        }, None

    except Error as e:
        print("DB ERROR in create_product:", e)
        if conn:
            conn.rollback()
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_products(search=None):
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
                c.category_name,
                COALESCE(i.quantity_available, 0) as quantity_available,
                p.reorder_level,
                p.selling_price,
                p.status
            FROM public."Products" p
            LEFT JOIN public."Categories" c ON p.category_id = c.category_id
            LEFT JOIN public."Inventory" i ON p.product_id = i.product_id
        '''

        parameters = []

        if search:
            query += " WHERE p.product_name ILIKE %s OR p.sku ILIKE %s"
            parameters.append(f"%{search}%")
            parameters.append(f"%{search}%")

        query += " ORDER BY p.product_id DESC"

        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

        products = []
        for row in rows:
            products.append({
                "product_id": row[0],
                "product_name": row[1],
                "sku": row[2],
                "category_name": row[3],
                "quantity_available": row[4],
                "reorder_level": row[5],
                "price": float(row[6]),
                "status": row[7]
            })

        return products, None

    except Error as e:
        print("DB ERROR in get_products:", e)
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_product(product_id, product_name, sku, category_id, reorder_level, price, status):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if SKU exists for another product
        cursor.execute(
            '''
            SELECT product_id
            FROM public."Products"
            WHERE sku = %s AND product_id != %s
            ''',
            (sku, product_id)
        )
        if cursor.fetchone():
            return None, "Another product with this SKU already exists"

        cursor.execute(
            '''
            UPDATE public."Products"
            SET product_name = %s, sku = %s, category_id = %s, reorder_level = %s, selling_price = %s, status = %s
            WHERE product_id = %s
            RETURNING product_id, product_name, sku, category_id, reorder_level, selling_price, status
            ''',
            (product_name, sku, category_id, reorder_level, price, status, product_id)
        )

        updated_product = cursor.fetchone()

        if updated_product is None:
            return None, "Product not found"
            
        # fetch quantity available
        cursor.execute('SELECT quantity_available FROM public."Inventory" WHERE product_id = %s', (product_id,))
        inv_row = cursor.fetchone()
        qty = inv_row[0] if inv_row else 0

        conn.commit()

        return {
            "product_id": updated_product[0],
            "product_name": updated_product[1],
            "sku": updated_product[2],
            "category_id": updated_product[3],
            "quantity_available": qty,
            "reorder_level": updated_product[4],
            "price": float(updated_product[5]),
            "status": updated_product[6]
        }, None

    except Error as e:
        print("DB ERROR in update_product:", e)
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

        # Simple delete logic
        cursor.execute(
            '''
            DELETE FROM public."Products"
            WHERE product_id = %s
            RETURNING product_id
            ''',
            (product_id,)
        )

        deleted = cursor.fetchone()

        if deleted is None:
            return False, "Product not found"

        conn.commit()
        return True, None

    except Error:
        if conn:
            conn.rollback()
        return False, "Database error - Product might be linked to transactions"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
