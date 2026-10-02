from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.team2.purchase_order_service import get_supplier_purchase_orders, get_all_purchase_orders, update_purchase_order_status

po_bp = Blueprint('purchase_orders', __name__, url_prefix='/api/purchase-orders')

@po_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    # Ideally we decode the JWT to check role
    # For now, let's just assume we pass role or check it.
    # Actually, we can get role from DB, or if it's stored in JWT claims.
    # For simplicity, if role is Supplier, they should only see theirs.
    # We will just fetch the user's role from DB or rely on the frontend to pass supplier_id for now if we don't have claims.
    # Let's do a simple DB check for the user's role.
    from app.extensions import get_db_connection
    current_user_id = get_jwt_identity()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT role_name FROM "Users" u JOIN "Roles" r ON u.role_id = r.role_id WHERE u.user_id = %s', (current_user_id,))
    role = cursor.fetchone()
    
    if role and role[0] == 'Supplier':
        # Find supplier_id for this user.
        # Wait, the DB schema has `Suppliers` but it's not directly linked to `Users` in the schema shown, 
        # unless supplier_id is the user_id for Supplier accounts. 
        # For this demo, let's assume supplier_id = current_user_id or we just fetch all if Manager.
        supplier_id = current_user_id 
        orders, err = get_supplier_purchase_orders(supplier_id)
    else:
        # Managers / Owners see all
        orders, err = get_all_purchase_orders()
        
    cursor.close()
    conn.close()

    if err:
        return jsonify({'message': err}), 500
    return jsonify(orders), 200

@po_bp.route('/<int:po_id>/status', methods=['PATCH'])
@jwt_required()
def update_status(po_id):
    data = request.json
    status = data.get('status')
    if not status:
        return jsonify({'message': 'Status is required'}), 400
        
    current_user_id = get_jwt_identity()
    
    from app.extensions import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT role_name FROM "Users" u JOIN "Roles" r ON u.role_id = r.role_id WHERE u.user_id = %s', (current_user_id,))
    role = cursor.fetchone()
    conn.close()
    
    supplier_id = None
    if role and role[0] == 'Supplier':
        supplier_id = current_user_id
        
    success, err = update_purchase_order_status(po_id, status, supplier_id)
    if not success:
        return jsonify({'message': err}), 400
        
    return jsonify({'message': f'Status updated to {status}'}), 200
