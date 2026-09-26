import logging
from flask import Blueprint, request
from ...services.team2.supplier_po_service import SupplierPurchaseOrderService
from ...utils.response import success_response, error_response
from ...utils.auth import require_supplier_auth

logger = logging.getLogger(__name__)

supplier_po_bp = Blueprint("supplier_po_bp", __name__, url_prefix="/api/team2/supplier/purchase-orders")

@supplier_po_bp.route("", methods=["GET"])
@require_supplier_auth
def get_purchase_orders(auth_data):
    """
    GET /api/team2/supplier/purchase-orders
    Returns all purchase orders assigned to the authenticated supplier.
    Optional query params: ?status=Pending|Accepted|Rejected|all, ?search=query
    """
    try:
        supplier_id = auth_data["supplier_id"]
        status_filter = request.args.get("status")
        search_query = request.args.get("search")

        orders = SupplierPurchaseOrderService.get_purchase_orders(
            supplier_id=supplier_id,
            status_filter=status_filter,
            search_query=search_query
        )
        return success_response(
            data=orders,
            message="Purchase orders retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_purchase_orders: {e}")
        return error_response(
            message="Failed to retrieve purchase orders",
            error=str(e),
            status_code=500
        )

@supplier_po_bp.route("/suppliers", methods=["GET"])
def get_suppliers():
    """
    GET /api/team2/supplier/purchase-orders/suppliers
    Returns all registered suppliers from the database.
    """
    try:
        suppliers = SupplierPurchaseOrderService.get_all_suppliers()
        return success_response(
            data=suppliers,
            message="Suppliers retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_suppliers: {e}")
        return error_response(
            message="Failed to retrieve suppliers",
            error=str(e),
            status_code=500
        )

@supplier_po_bp.route("/current-supplier", methods=["GET"])
@require_supplier_auth
def get_current_supplier(auth_data):
    """
    GET /api/team2/supplier/purchase-orders/current-supplier
    Returns profile information for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        from ...services.team2.supplier_dashboard_service import SupplierDashboardService
        profile = SupplierDashboardService.get_supplier_info(supplier_id)
        return success_response(
            data=profile,
            message="Current supplier profile retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_current_supplier: {e}")
        return error_response(
            message="Failed to retrieve current supplier profile",
            error=str(e),
            status_code=500
        )

@supplier_po_bp.route("/<int:po_id>", methods=["GET"])
@require_supplier_auth
def get_purchase_order_details(auth_data, po_id):
    """
    GET /api/team2/supplier/purchase-orders/<po_id>
    Returns detailed purchase order information including line items.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        po_details = SupplierPurchaseOrderService.get_purchase_order_details(
            supplier_id=supplier_id,
            po_id=po_id
        )
        if not po_details:
            return error_response(
                message=f"Purchase order PO-{po_id} not found",
                status_code=404
            )
        return success_response(
            data=po_details,
            message="Purchase order details retrieved successfully"
        )
    except PermissionError as pe:
        return error_response(
            message=str(pe),
            status_code=403
        )
    except Exception as e:
        logger.error(f"Error in get_purchase_order_details: {e}")
        return error_response(
            message="Failed to retrieve purchase order details",
            error=str(e),
            status_code=500
        )

@supplier_po_bp.route("/<int:po_id>/accept", methods=["POST"])
@require_supplier_auth
def accept_purchase_order(auth_data, po_id):
    """
    POST /api/team2/supplier/purchase-orders/<po_id>/accept
    Accepts a purchase order by the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        updated_po = SupplierPurchaseOrderService.accept_purchase_order(
            supplier_id=supplier_id,
            po_id=po_id
        )
        return success_response(
            data=updated_po,
            message=f"Purchase order PO-{po_id:04d} accepted successfully"
        )
    except PermissionError as pe:
        return error_response(
            message=str(pe),
            status_code=403
        )
    except ValueError as ve:
        return error_response(
            message=str(ve),
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error accepting purchase order: {e}")
        return error_response(
            message="Failed to accept purchase order",
            error=str(e),
            status_code=500
        )

@supplier_po_bp.route("/<int:po_id>/reject", methods=["POST"])
@require_supplier_auth
def reject_purchase_order(auth_data, po_id):
    """
    POST /api/team2/supplier/purchase-orders/<po_id>/reject
    Rejects a purchase order with an optional rejection reason.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        reason = body.get("reason", "").strip()

        updated_po = SupplierPurchaseOrderService.reject_purchase_order(
            supplier_id=supplier_id,
            po_id=po_id,
            reason=reason
        )
        return success_response(
            data=updated_po,
            message=f"Purchase order PO-{po_id:04d} has been rejected"
        )
    except PermissionError as pe:
        return error_response(
            message=str(pe),
            status_code=403
        )
    except ValueError as ve:
        return error_response(
            message=str(ve),
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error rejecting purchase order: {e}")
        return error_response(
            message="Failed to reject purchase order",
            error=str(e),
            status_code=500
        )
