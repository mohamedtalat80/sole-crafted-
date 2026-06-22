from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.core.exceptions import ApplicationError
from apps.core.pagination import PaginationMixin
from apps.core.permissions import IsAdminAccount
from apps.core.responses import error_response, success_response
from apps.inventory.repositories.inventory_repository import InventoryRepository
from apps.inventory.serializers import (
    InventorySnapshotSerializer,
    StockAdjustmentWriteSerializer,
    StockEntrySerializer,
)
from apps.inventory.services.inventory_service import InventoryService


def _get_inventory_service() -> InventoryService:
    return InventoryService(repository=InventoryRepository())


# ---------------------------------------------------------------------------
# Admin: list all current stock levels
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminInventoryListView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_inventory_list",
        summary="List current stock levels for all products",
        responses={200: InventorySnapshotSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Inventory List",
                value={
                    "status": True,
                    "message": "Stock levels retrieved successfully",
                    "data": {
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [
                            {"id": 1, "product": "Air Max", "size": "42", "colour": "Black", "quantity_on_hand": 10, "updated_at": "2026-01-01T00:00:00Z"}
                        ],
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            service = _get_inventory_service()
            snapshots = service.get_all_stock()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(snapshots, InventorySnapshotSerializer, request, "Stock levels retrieved successfully")


# ---------------------------------------------------------------------------
# Admin: stock levels for a single product
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminProductStockView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_product_stock",
        summary="List current stock for a single product (all size/colour combinations)",
        responses={200: InventorySnapshotSerializer(many=True), 404: {"description": "Product not found"}},
    )
    def get(self, request, product_id: int):
        try:
            service = _get_inventory_service()
            snapshots = service.get_product_stock(product_id)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(snapshots, InventorySnapshotSerializer, request, "Product stock retrieved successfully")


# ---------------------------------------------------------------------------
# Admin: stock movement history for a single product
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminProductStockHistoryView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_product_stock_history",
        summary="List stock movement history for a single product",
        responses={200: StockEntrySerializer(many=True), 404: {"description": "Product not found"}},
    )
    def get(self, request, product_id: int):
        try:
            service = _get_inventory_service()
            entries = service.get_product_history(product_id)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(entries, StockEntrySerializer, request, "Stock history retrieved successfully")


# ---------------------------------------------------------------------------
# Admin: stock-in
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminStockInView(APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_stock_in",
        summary="Record a stock-in (receiving new units)",
        request=StockAdjustmentWriteSerializer,
        responses={200: InventorySnapshotSerializer, 400: {"description": "Invalid data"}, 404: {"description": "Product / Size / Colour not found"}},
        examples=[
            OpenApiExample(
                "Stock In",
                value={"product_id": 1, "size_id": 2, "colour_id": 3, "quantity": 50, "note": "Received from supplier"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = StockAdjustmentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            service = _get_inventory_service()
            snapshot = service.record_stock_in(
                product_id=d["product_id"],
                size_id=d["size_id"],
                colour_id=d["colour_id"],
                quantity=d["quantity"],
                note=d["note"],
                recorded_by=request.user,
            )
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=InventorySnapshotSerializer(snapshot).data,
            message="Stock-in recorded successfully",
        )


# ---------------------------------------------------------------------------
# Admin: stock-out
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminStockOutView(APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_stock_out",
        summary="Record a stock-out (dispatching units)",
        request=StockAdjustmentWriteSerializer,
        responses={200: InventorySnapshotSerializer, 400: {"description": "Invalid data or insufficient stock"}, 404: {"description": "Product / Size / Colour not found"}},
        examples=[
            OpenApiExample(
                "Stock Out",
                value={"product_id": 1, "size_id": 2, "colour_id": 3, "quantity": 5, "note": "Order #1042"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = StockAdjustmentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            service = _get_inventory_service()
            snapshot = service.record_stock_out(
                product_id=d["product_id"],
                size_id=d["size_id"],
                colour_id=d["colour_id"],
                quantity=d["quantity"],
                note=d["note"],
                recorded_by=request.user,
            )
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=InventorySnapshotSerializer(snapshot).data,
            message="Stock-out recorded successfully",
        )


# ---------------------------------------------------------------------------
# Admin: adjustment (set absolute quantity)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Inventory"])
class AdminStockAdjustmentView(APIView):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_stock_adjustment",
        summary="Set an absolute stock quantity (inventory count correction)",
        request=StockAdjustmentWriteSerializer,
        responses={200: InventorySnapshotSerializer, 400: {"description": "Invalid data"}, 404: {"description": "Product / Size / Colour not found"}},
        examples=[
            OpenApiExample(
                "Stock Adjustment",
                value={"product_id": 1, "size_id": 2, "colour_id": 3, "quantity": 30, "note": "Annual stock count correction"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = StockAdjustmentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            service = _get_inventory_service()
            snapshot = service.record_adjustment(
                product_id=d["product_id"],
                size_id=d["size_id"],
                colour_id=d["colour_id"],
                quantity=d["quantity"],
                note=d["note"],
                recorded_by=request.user,
            )
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=InventorySnapshotSerializer(snapshot).data,
            message="Stock adjustment recorded successfully",
        )
