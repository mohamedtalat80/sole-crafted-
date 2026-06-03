from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.exceptions import ApplicationError
from apps.core.pagination import PaginationMixin
from apps.core.responses import error_response, success_response
from apps.products.repositories.products_repository import ProductRepository
from apps.products.serializers import ProductDetailSerializer, ProductListSerializer
from apps.products.services.products_service import ProductService


def _get_product_service() -> ProductService:
    return ProductService(repository=ProductRepository())


# ---------------------------------------------------------------------------
# Public: list available products
# ---------------------------------------------------------------------------

@extend_schema(tags=["Products"])
class ProductListView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="product_list",
        summary="List available products",
        responses={200: ProductListSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Product List Response",
                value={
                    "status": True,
                    "message": "Products retrieved successfully",
                    "data": {
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [
                            {
                                "id": 1,
                                "name": "Air Max",
                                "brand": "Nike",
                                "price": "199.99",
                                "discount_percentage": 10,
                                "is_available": True,
                                "main_image": "https://example.com/image.jpg",
                                "description": "Classic running shoe.",
                                "sizes": {"EU": [40, 41, 42]},
                            }
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
            service = _get_product_service()
            products = service.list_available_products()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(products, ProductListSerializer, request, "Products retrieved successfully")


# ---------------------------------------------------------------------------
# Public: retrieve product detail
# ---------------------------------------------------------------------------

@extend_schema(tags=["Products"])
class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="product_retrieve",
        summary="Retrieve a product",
        responses={200: ProductDetailSerializer, 404: {"description": "Product not found"}},
    )
    def get(self, request, pk: int):
        try:
            service = _get_product_service()
            product = service.get_product(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ProductDetailSerializer(product, context={"request": request}).data,
            message="Product retrieved successfully",
        )
