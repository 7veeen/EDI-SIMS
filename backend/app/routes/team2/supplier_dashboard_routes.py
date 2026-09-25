import logging
from flask import Blueprint, request
from ...services.team2.supplier_dashboard_service import SupplierDashboardService
from ...utils.response import success_response, error_response
from ...utils.auth import require_supplier_auth

logger = logging.getLogger(__name__)

supplier_dashboard_bp = Blueprint("supplier_dashboard_bp", __name__, url_prefix="/api/team2/supplier")

@supplier_dashboard_bp.route("/dashboard", methods=["GET"])
@require_supplier_auth
def get_dashboard_data(auth_data):
    """
    GET /api/team2/supplier/dashboard
    Returns all aggregated dashboard data for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        dashboard_data = SupplierDashboardService.get_full_dashboard(supplier_id)
        return success_response(
            data=dashboard_data,
            message="Supplier dashboard retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {e}")
        return error_response(
            message="Failed to retrieve supplier dashboard data",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/summary-cards", methods=["GET"])
@require_supplier_auth
def get_summary_cards(auth_data):
    """
    GET /api/team2/supplier/summary-cards
    Returns the 6 summary card counts for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        counts = SupplierDashboardService.get_summary_counts(supplier_id)
        return success_response(
            data=counts,
            message="Summary counts retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_summary_cards: {e}")
        return error_response(
            message="Failed to retrieve summary counts",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/recent-stock-requests", methods=["GET"])
@require_supplier_auth
def get_recent_stock_requests(auth_data):
    """
    GET /api/team2/supplier/recent-stock-requests
    Returns recent stock requests for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        limit = int(request.args.get("limit", 5))
        requests_list = SupplierDashboardService.get_recent_stock_requests(supplier_id, limit=limit)
        return success_response(
            data=requests_list,
            message="Recent stock requests retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_recent_stock_requests: {e}")
        return error_response(
            message="Failed to retrieve recent stock requests",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/recent-purchase-orders", methods=["GET"])
@require_supplier_auth
def get_recent_purchase_orders(auth_data):
    """
    GET /api/team2/supplier/recent-purchase-orders
    Returns recent purchase orders for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        limit = int(request.args.get("limit", 5))
        pos_list = SupplierDashboardService.get_recent_purchase_orders(supplier_id, limit=limit)
        return success_response(
            data=pos_list,
            message="Recent purchase orders retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_recent_purchase_orders: {e}")
        return error_response(
            message="Failed to retrieve recent purchase orders",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/pending-shipments", methods=["GET"])
@require_supplier_auth
def get_pending_shipments(auth_data):
    """
    GET /api/team2/supplier/pending-shipments
    Returns pending shipments / orders to ship for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        limit = int(request.args.get("limit", 5))
        shipments = SupplierDashboardService.get_pending_shipments(supplier_id, limit=limit)
        return success_response(
            data=shipments,
            message="Pending shipments retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_pending_shipments: {e}")
        return error_response(
            message="Failed to retrieve pending shipments",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/notifications", methods=["GET"])
@require_supplier_auth
def get_notifications(auth_data):
    """
    GET /api/team2/supplier/notifications
    Returns recent notifications for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        limit = int(request.args.get("limit", 5))
        notifications = SupplierDashboardService.get_recent_notifications(supplier_id, limit=limit)
        return success_response(
            data=notifications,
            message="Recent notifications retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_notifications: {e}")
        return error_response(
            message="Failed to retrieve notifications",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/profile", methods=["GET"])
@require_supplier_auth
def get_supplier_profile(auth_data):
    """
    GET /api/team2/supplier/profile
    Returns profile information for the authenticated supplier.
    """
    try:
        supplier_id = auth_data["supplier_id"]
        supplier_info = SupplierDashboardService.get_supplier_info(supplier_id)
        return success_response(
            data=supplier_info,
            message="Supplier profile retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error in get_supplier_profile: {e}")
        return error_response(
            message="Failed to retrieve supplier profile",
            error=str(e),
            status_code=500
        )

@supplier_dashboard_bp.route("/health", methods=["GET"])
def health_check():
    """
    GET /api/team2/supplier/health
    Basic service health check.
    """
    from ...config.config import Config
    return success_response(
        data={
            "service": "Team 2 Supplier Dashboard Service",
            "status": "healthy",
            "supabase_configured": Config.is_supabase_configured()
        },
        message="Service is operational"
    )
