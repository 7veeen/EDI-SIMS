from flask import Blueprint, jsonify, request
# pyrefly: ignore [missing-import]
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import get_db_connection
from psycopg2 import Error

quotations_bp = Blueprint('quotations', __name__, url_prefix='/api/quotations')

def get_role_and_supplier(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT role_name FROM "Users" u JOIN "Roles" r ON u.role_id = r.role_id WHERE u.user_id = %s', (user_id,))
    role = cursor.fetchone()
    
    if role and role[0] == 'Supplier':
        cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE supplier_id = %s', (user_id,))
        supp = cursor.fetchone()
        cursor.close()
        conn.close()
        return role[0], user_id if supp else None
    
    cursor.close()
    conn.close()
    return role[0] if role else None, None

@quotations_bp.route('/', methods=['GET'])
@jwt_required()
def get_quotations():
    current_user_id = get_jwt_identity()
    role, supplier_id = get_role_and_supplier(current_user_id)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == 'Supplier':
            if not supplier_id:
                return jsonify({'message': 'Supplier profile not found'}), 404
            cursor.execute('''
                SELECT q.quotation_id, q.product_id, p.product_name, p.sku, q.quantity, q.quoted_price, (q.quoted_price * q.quantity) as subtotal, 
                       q.quotation_date, q.valid_until, q.status, q.quoted_price
                FROM "SupplierQuotations" q
                JOIN "Products" p ON q.product_id = p.product_id
                WHERE q.supplier_id = %s
                ORDER BY q.quotation_date DESC
            ''', (supplier_id,))
        else:
            cursor.execute('''
                SELECT q.quotation_id, q.product_id, p.product_name, p.sku, q.quantity, q.quoted_price, (q.quoted_price * q.quantity) as subtotal, 
                       q.quotation_date, q.valid_until, q.status, q.quoted_price
                FROM "SupplierQuotations" q
                JOIN "Products" p ON q.product_id = p.product_id
                ORDER BY q.quotation_date DESC
            ''')
            
        rows = cursor.fetchall()
        quotations = []
        for r in rows:
            quotations.append({
                'quotation_id': r[0],
                'product_id': r[1],
                'product_name': r[2],
                'sku': r[3],
                'quantity': r[4],
                'unit_price': float(r[5]) if r[5] else 0.0,
                'subtotal': float(r[6]) if r[6] else 0.0,
                'quotation_date': r[7].isoformat() if r[7] else None,
                'valid_until': r[8].isoformat() if r[8] else None,
                'status': r[9],
                'quoted_price': float(r[10]) if r[10] else 0.0,
            })
        return jsonify(quotations), 200
    except Error as e:
        print("DB ERROR in get_quotations:", e)
        return jsonify({'message': 'Database error'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@quotations_bp.route('/', methods=['POST'])
@jwt_required()
def create_quotation():
    current_user_id = get_jwt_identity()
    role, supplier_id = get_role_and_supplier(current_user_id)
    
    if role != 'Supplier':
        return jsonify({'message': 'Only suppliers can create quotations'}), 403
        
    if not supplier_id:
        return jsonify({'message': 'Supplier profile not found for this user.'}), 400
        
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    unit_price = data.get('unit_price')
    valid_until = data.get('valid_until')
    
    if not all([product_id, quantity, unit_price, valid_until]):
        return jsonify({'message': 'Missing required fields'}), 400
        
    try:
        quantity = int(quantity)
        unit_price = float(unit_price)
    except ValueError:
        return jsonify({'message': 'Invalid numeric values'}), 400
        
    if quantity <= 0:
        return jsonify({'message': 'Quantity must be greater than 0'}), 400
    if unit_price < 0:
        return jsonify({'message': 'Unit price cannot be negative'}), 400
        
    subtotal = quantity * unit_price
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify product exists
        cursor.execute('SELECT product_id FROM "Products" WHERE product_id = %s', (product_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'Product not found'}), 404
            
        cursor.execute('''
            INSERT INTO "SupplierQuotations" (supplier_id, product_id, quotation_date, quoted_price, quantity, valid_until, status)
            VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, 'Pending')
            RETURNING quotation_id
        ''', (supplier_id, product_id, unit_price, quantity, valid_until))
        
        quotation_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'message': 'Quotation created successfully', 'quotation_id': quotation_id}), 201
    except Error as e:
        if conn: conn.rollback()
        print("DB ERROR in create_quotation:", e)
        return jsonify({'message': 'Database error'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@quotations_bp.route('/<int:quotation_id>/status', methods=['PATCH'])
@jwt_required()
def update_status(quotation_id):
    current_user_id = get_jwt_identity()
    role, supplier_id = get_role_and_supplier(current_user_id)
    
    data = request.json
    status = data.get('status')
    if not status:
        return jsonify({'message': 'Status is required'}), 400
        
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == 'Supplier':
            if not supplier_id:
                return jsonify({'message': 'Supplier profile not found'}), 404
            cursor.execute('''
                UPDATE "SupplierQuotations"
                SET status = %s
                WHERE quotation_id = %s AND supplier_id = %s
                RETURNING quotation_id
            ''', (status, quotation_id, supplier_id))
        else:
            cursor.execute('''
                UPDATE "SupplierQuotations"
                SET status = %s
                WHERE quotation_id = %s
                RETURNING quotation_id
            ''', (status, quotation_id))
            
        if not cursor.fetchone():
            return jsonify({'message': 'Quotation not found or permission denied'}), 404
            
        conn.commit()
        return jsonify({'message': f'Status updated to {status}'}), 200
    except Error as e:
        if conn: conn.rollback()
        print("DB ERROR in update_status:", e)
        return jsonify({'message': 'Database error'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@quotations_bp.route('/<int:quotation_id>', methods=['PUT'])
@jwt_required()
def edit_quotation(quotation_id):
    current_user_id = get_jwt_identity()
    role, supplier_id = get_role_and_supplier(current_user_id)
    
    if role != 'Supplier':
        return jsonify({'message': 'Only suppliers can edit quotations'}), 403
        
    if not supplier_id:
        return jsonify({'message': 'Supplier profile not found'}), 404
        
    data = request.json
    quantity = data.get('quantity')
    unit_price = data.get('unit_price')
    valid_until = data.get('valid_until')
    
    if not all([quantity, unit_price, valid_until]):
        return jsonify({'message': 'Missing required fields'}), 400
        
    try:
        quantity = int(quantity)
        unit_price = float(unit_price)
    except ValueError:
        return jsonify({'message': 'Invalid numeric values'}), 400
        
    if quantity <= 0:
        return jsonify({'message': 'Quantity must be greater than 0'}), 400
    if unit_price < 0:
        return jsonify({'message': 'Unit price cannot be negative'}), 400
        
    subtotal = quantity * unit_price
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if quotation exists and belongs to supplier, and status is allowed
        cursor.execute('''
            SELECT status FROM "SupplierQuotations"
            WHERE quotation_id = %s AND supplier_id = %s
        ''', (quotation_id, supplier_id))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'message': 'Quotation not found or access denied'}), 404
            
        status = row[0]
        if status not in ['Pending', 'Revision']:
            return jsonify({'message': 'Quotation cannot be edited in its current status'}), 400
            
        cursor.execute('''
            UPDATE "SupplierQuotations"
            SET quantity = %s, quoted_price = %s, valid_until = %s
            WHERE quotation_id = %s AND supplier_id = %s
        ''', (quantity, unit_price, valid_until, quotation_id, supplier_id))
        
        conn.commit()
        return jsonify({'message': 'Quotation updated successfully'}), 200
    except Error as e:
        if conn: conn.rollback()
        print("DB ERROR in edit_quotation:", e)
        return jsonify({'message': 'Database error'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
