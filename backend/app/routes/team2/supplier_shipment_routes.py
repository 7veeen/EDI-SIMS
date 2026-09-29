import logging
from flask import Blueprint, request
from ...services.team2.supplier_shipment_service import SupplierShipmentService
from ...utils.response import success_response, error_response
from ...utils.auth import require_supplier_auth

logger = logging.getLogger(__name__)

supplier_shipment_bp = Blueprint("supplier_shipment_bp", __name__, url_prefix="/api/team2/supplier")

# ====================================================================
# 1. SHIPMENT FULFILLMENT ENDPOINTS
# ====================================================================

@supplier_shipment_bp.route("/shipments", methods=["GET"])
@require_supplier_auth
def get_shipments(auth_data):
    """
    GET /api/team2/supplier/shipments
    Returns all active shipments for the authenticated supplier.
    Query params: ?status=Ready for Shipment|In Transit|Shipped|Delivered|all, ?search=query
    """
    try:
        supplier_id = auth_data["supplier_id"]
        status_filter = request.args.get("status")
        search_query = request.args.get("search")

        shipments = SupplierShipmentService.get_shipments(
            supplier_id=supplier_id,
            status_filter=status_filter,
            search_query=search_query
        )
        return success_response(
            data=shipments,
            message="Shipments retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_shipments: {e}")
        return error_response(
            message="Failed to retrieve shipments",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/ready-to-ship", methods=["GET"])
@require_supplier_auth
def get_orders_ready_to_ship(auth_data):
    """
    GET /api/team2/supplier/shipments/ready-to-ship
    Returns accepted purchase orders that need packaging or are ready for shipment.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        orders = SupplierShipmentService.get_orders_ready_to_ship(supplier_id)
        return success_response(
            data=orders,
            message="Ready-to-ship purchase orders retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_orders_ready_to_ship: {e}")
        return error_response(
            message="Failed to retrieve orders ready for shipment",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/completed", methods=["GET"])
@require_supplier_auth
def get_completed_shipments(auth_data):
    """
    GET /api/team2/supplier/shipments/completed
    Returns all delivered and fulfilled shipments for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        search_query = request.args.get("search")
        completed = SupplierShipmentService.get_completed_shipments(
            supplier_id=supplier_id,
            search_query=search_query
        )
        return success_response(
            data=completed,
            message="Completed shipments retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_completed_shipments: {e}")
        return error_response(
            message="Failed to retrieve completed shipments",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/stats", methods=["GET"])
@require_supplier_auth
def get_fulfillment_stats(auth_data):
    """
    GET /api/team2/supplier/shipments/stats
    Returns aggregated fulfillment and history statistics for summary cards.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        stats = SupplierShipmentService.get_fulfillment_stats(supplier_id)
        return success_response(
            data=stats,
            message="Fulfillment statistics retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_fulfillment_stats: {e}")
        return error_response(
            message="Failed to retrieve fulfillment stats",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/<int:shipment_id>", methods=["GET"])
@require_supplier_auth
def get_shipment_details(auth_data, shipment_id):
    """
    GET /api/team2/supplier/shipments/<shipment_id>
    Returns details for a single shipment including items and tracking history.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        details = SupplierShipmentService.get_shipment_details(supplier_id, shipment_id)
        if not details:
            return error_response(
                message=f"Shipment #{shipment_id} not found",
                status_code=404
            )
        return success_response(
            data=details,
            message="Shipment details retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_shipment_details: {e}")
        return error_response(
            message="Failed to retrieve shipment details",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/ready", methods=["POST"])
@require_supplier_auth
def mark_order_ready_for_shipment(auth_data):
    """
    POST /api/team2/supplier/shipments/ready
    Marks an accepted order ready for carrier packaging and dispatch.
    Body: { "purchase_order_id": 4, "notes": "Optional packaging notes" }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        po_id = body.get("purchase_order_id")
        notes = body.get("notes")

        if not po_id:
            return error_response(
                message="purchase_order_id is required",
                status_code=400
            )

        result = SupplierShipmentService.mark_order_ready_for_shipment(
            supplier_id=supplier_id,
            po_id=int(po_id),
            notes=notes
        )
        return success_response(
            data=result,
            message=f"Order PO-{int(po_id):04d} marked ready for shipment"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except Exception as e:
        logger.error(f"Error in mark_order_ready_for_shipment: {e}")
        return error_response(
            message="Failed to mark order ready for shipment",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/details", methods=["POST"])
@require_supplier_auth
def enter_shipment_details(auth_data):
    """
    POST /api/team2/supplier/shipments/details
    Enters full shipment details (carrier, tracking number, package info, notes).
    Body: { "purchase_order_id": 4, "carrier": "BlueDart", "tracking_number": "...", ... }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        po_id = body.get("purchase_order_id")

        if not po_id:
            return error_response(
                message="purchase_order_id is required",
                status_code=400
            )

        result = SupplierShipmentService.enter_shipment_details(
            supplier_id=supplier_id,
            po_id=int(po_id),
            details=body
        )
        return success_response(
            data=result,
            message=f"Shipment details recorded for PO-{int(po_id):04d}"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except Exception as e:
        logger.error(f"Error in enter_shipment_details: {e}")
        return error_response(
            message="Failed to record shipment details",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/<int:shipment_id>/mark-shipped", methods=["POST"])
@require_supplier_auth
def mark_as_shipped(auth_data, shipment_id):
    """
    POST /api/team2/supplier/shipments/<shipment_id>/mark-shipped
    Marks a shipment as dispatched / shipped.
    Body: { "carrier": "FedEx", "tracking_number": "...", "expected_delivery": "2026-10-05", "notes": "..." }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}

        result = SupplierShipmentService.mark_as_shipped(
            supplier_id=supplier_id,
            shipment_id=shipment_id,
            carrier=body.get("carrier"),
            tracking_number=body.get("tracking_number"),
            expected_delivery=body.get("expected_delivery"),
            notes=body.get("notes")
        )
        return success_response(
            data=result,
            message=f"Shipment #{shipment_id} successfully marked as shipped"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except Exception as e:
        logger.error(f"Error in mark_as_shipped: {e}")
        return error_response(
            message="Failed to mark shipment as shipped",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/<int:shipment_id>/status", methods=["PUT"])
@require_supplier_auth
def update_shipment_status(auth_data, shipment_id):
    """
    PUT /api/team2/supplier/shipments/<shipment_id>/status
    Updates the transit status of an ongoing shipment.
    Body: { "status": "In Transit", "location": "Mumbai Hub", "notes": "Checkpoint scan" }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        new_status = body.get("status")
        location = body.get("location")
        notes = body.get("notes")

        if not new_status:
            return error_response(
                message="status is required",
                status_code=400
            )

        result = SupplierShipmentService.update_shipment_status(
            supplier_id=supplier_id,
            shipment_id=shipment_id,
            new_status=new_status,
            location=location,
            notes=notes
        )
        return success_response(
            data=result,
            message=f"Shipment #{shipment_id} status updated to {new_status}"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except ValueError as ve:
        return error_response(message=str(ve), status_code=400)
    except Exception as e:
        logger.error(f"Error in update_shipment_status: {e}")
        return error_response(
            message="Failed to update shipment status",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/<int:shipment_id>/expected-delivery", methods=["PUT"])
@require_supplier_auth
def update_expected_delivery(auth_data, shipment_id):
    """
    PUT /api/team2/supplier/shipments/<shipment_id>/expected-delivery
    Updates the expected delivery date for a shipment and purchase order.
    Body: { "expected_delivery": "2026-10-06", "reason": "Courier reschedule" }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        expected_delivery = body.get("expected_delivery")
        reason = body.get("reason")

        if not expected_delivery:
            return error_response(
                message="expected_delivery date is required (YYYY-MM-DD)",
                status_code=400
            )

        result = SupplierShipmentService.update_expected_delivery(
            supplier_id=supplier_id,
            shipment_id=shipment_id,
            expected_delivery=expected_delivery,
            reason=reason
        )
        return success_response(
            data=result,
            message="Expected delivery date updated successfully"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except Exception as e:
        logger.error(f"Error in update_expected_delivery: {e}")
        return error_response(
            message="Failed to update expected delivery date",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/shipments/<int:shipment_id>/mark-delivered", methods=["POST"])
@require_supplier_auth
def mark_as_delivered(auth_data, shipment_id):
    """
    POST /api/team2/supplier/shipments/<shipment_id>/mark-delivered
    Marks shipment as delivered to recipient dock.
    Body: { "notes": "Signed by receiving officer" }
    """
    try:
        supplier_id = auth_data["supplier_id"]
        body = request.get_json(silent=True) or {}
        notes = body.get("notes")

        result = SupplierShipmentService.mark_as_delivered(
            supplier_id=supplier_id,
            shipment_id=shipment_id,
            notes=notes
        )
        return success_response(
            data=result,
            message=f"Shipment #{shipment_id} confirmed and marked as delivered"
        )
    except PermissionError as pe:
        return error_response(message=str(pe), status_code=403)
    except Exception as e:
        logger.error(f"Error in mark_as_delivered: {e}")
        return error_response(
            message="Failed to mark shipment as delivered",
            error=str(e),
            status_code=500
        )

# ====================================================================
# 2. PREVIOUS RECORDS & HISTORY ENDPOINTS
# ====================================================================

@supplier_shipment_bp.route("/history/purchase-orders", methods=["GET"])
@require_supplier_auth
def get_previous_purchase_orders(auth_data):
    """
    GET /api/team2/supplier/history/purchase-orders
    Returns previous/historical purchase orders with line items and status.
    Query params: ?status=Accepted|Delivered|Rejected|all, ?search=query
    """
    try:
        supplier_id = auth_data["supplier_id"]
        status_filter = request.args.get("status")
        search_query = request.args.get("search")

        orders = SupplierShipmentService.get_previous_purchase_orders(
            supplier_id=supplier_id,
            status_filter=status_filter,
            search_query=search_query
        )
        return success_response(
            data=orders,
            message="Previous purchase orders retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_previous_purchase_orders: {e}")
        return error_response(
            message="Failed to retrieve previous purchase orders",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/history/quotations", methods=["GET"])
@require_supplier_auth
def get_previous_quotations(auth_data):
    """
    GET /api/team2/supplier/history/quotations
    Returns previous quotations submitted by the authenticated supplier.
    Query params: ?status=Accepted|Pending|Expired|all, ?search=query
    """
    try:
        supplier_id = auth_data["supplier_id"]
        status_filter = request.args.get("status")
        search_query = request.args.get("search")

        quotations = SupplierShipmentService.get_previous_quotations(
            supplier_id=supplier_id,
            status_filter=status_filter,
            search_query=search_query
        )
        return success_response(
            data=quotations,
            message="Previous quotations retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_previous_quotations: {e}")
        return error_response(
            message="Failed to retrieve previous quotations",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/history/order/<int:po_id>", methods=["GET"])
@require_supplier_auth
def get_order_status_history_by_po(auth_data, po_id):
    """
    GET /api/team2/supplier/history/order/<po_id>
    Returns chronological event timeline for a specific purchase order.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        timeline = SupplierShipmentService.get_order_status_history(
            supplier_id=supplier_id,
            po_id=po_id
        )
        return success_response(
            data=timeline,
            message=f"Status history for PO-{po_id:04d} retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_order_status_history_by_po: {e}")
        return error_response(
            message="Failed to retrieve order status history",
            error=str(e),
            status_code=500
        )

@supplier_shipment_bp.route("/history/all", methods=["GET"])
@require_supplier_auth
def get_all_status_history(auth_data):
    """
    GET /api/team2/supplier/history/all
    Returns chronological event timeline across all orders and shipments for the supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        shipment_id = request.args.get("shipment_id")
        po_id = request.args.get("purchase_order_id")

        timeline = SupplierShipmentService.get_order_status_history(
            supplier_id=supplier_id,
            po_id=int(po_id) if po_id else None,
            shipment_id=int(shipment_id) if shipment_id else None
        )
        return success_response(
            data=timeline,
            message="All status history events retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_all_status_history: {e}")
        return error_response(
            message="Failed to retrieve status history",
            error=str(e),
            status_code=500
        )
