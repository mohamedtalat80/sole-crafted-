from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.exceptions import ApplicationError
from apps.core.pagination import PAGINATION_PARAMS, PaginationMixin, StandardResultsPagination
from apps.core.permissions import IsAdminAccount
from apps.core.responses import error_response, success_response
from apps.core.utils.translation_utils import TranslationService
from apps.products.repositories.products_repository import (
    CategoryRepository,
    ColourRepository,
    ProductRepository,
    SizeRepository,
    TagRepository,
)
from apps.products.serializers import (
    CategoryAdminReadSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    ColourAdminReadSerializer,
    ColourSerializer,
    ColourWriteSerializer,
    ProductAdminReadSerializer,
    ProductReadSerializer,
    ProductWriteSerializer,
    SizeSerializer,
    SizeWriteSerializer,
    TagAdminReadSerializer,
    TagSerializer,
    TagWriteSerializer,
)
from apps.products.services.products_service import (
    CategoryService,
    ColourService,
    ProductService,
    SizeService,
    TagService,
)

_ACCEPT_LANGUAGE_PARAM = OpenApiParameter(
    name="Accept-Language",
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Language for response content. "
        "Accepted: en (default), ar, nl, ru, pt, fr, de, hi, ko, es."
    ),
    enum=["en", "ar", "nl", "ru", "pt", "fr", "de", "hi", "ko", "es"],
    default="en",
)


# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------

def _get_product_service() -> ProductService:
    return ProductService(
        repository=ProductRepository(
            category=CategoryRepository(),
            tag=TagRepository(),
            colour=ColourRepository(),
            size=SizeRepository(),
        ),
        translation_service=TranslationService(api_key=settings.API_TRANSLATION_KEY),
    )


def _get_category_service() -> CategoryService:
    return CategoryService(
        repository=CategoryRepository(),
        translation_service=TranslationService(api_key=settings.API_TRANSLATION_KEY),
    )


def _get_tag_service() -> TagService:
    return TagService(
        repository=TagRepository(),
        translation_service=TranslationService(api_key=settings.API_TRANSLATION_KEY),
    )


def _get_colour_service() -> ColourService:
    return ColourService(
        repository=ColourRepository(),
        translation_service=TranslationService(api_key=settings.API_TRANSLATION_KEY),
    )


def _get_size_service() -> SizeService:
    return SizeService(repository=SizeRepository())


# ---------------------------------------------------------------------------
# Pagination helper for ViewSets
# ---------------------------------------------------------------------------

def _paginate(request, queryset, serializer_class, message: str):
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        data = serializer_class(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response_with_message(data, message)
    return success_response(
        data=serializer_class(queryset, many=True, context={"request": request}).data,
        message=message,
    )


# ---------------------------------------------------------------------------
# Public — Products
# ---------------------------------------------------------------------------

@extend_schema(tags=["Products"])
class ProductPublicListView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="product_public_list",
        summary="List available products",
        parameters=[_ACCEPT_LANGUAGE_PARAM, *PAGINATION_PARAMS],
        responses={200: ProductReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Product List Response",
                value={
                    "status": True,
                    "message": "Products retrieved successfully",
                    "data": {
                        "count": 1, "next": None, "previous": None, "next_pages": None,
                        "results": [{
                            "id": 1, "name": "Air Max", "brand": "Nike",
                            "price": "199.99", "discount_percentage": "10.00",
                            "description": "Classic running shoe.",
                            "sizes": [{"id": 1, "name": "42"}],
                            "colors": [{"id": 1, "name": "Black"}],
                            "category": {"id": 1, "name": "Running"},
                            "tags": [{"id": 1, "name": "Sport"}],
                            "images": [], "main_image": None,
                        }],
                    },
                },
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            service = _get_product_service()
            products = service.list_available_products()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(products, ProductReadSerializer, request, "Products retrieved successfully")


# ---------------------------------------------------------------------------
# Admin — Product
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Product"])
class AdminProductViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_product_list",
        summary="List all products",
        parameters=[*PAGINATION_PARAMS],
        responses={200: ProductAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Product List",
                value={"status": True, "message": "Products retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "next_pages": None, "results": [{"id": 1, "name": "Air Max", "brand": "Nike", "price": "199.99", "is_active": True}]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def list(self, request):
        try:
            products = _get_product_service().get_all_products()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return _paginate(request, products, ProductAdminReadSerializer, "Products retrieved successfully")

    @extend_schema(
        operation_id="admin_product_create",
        summary="Create a product",
        request=ProductWriteSerializer,
        responses={201: ProductAdminReadSerializer, 400: {"description": "Validation error"}},
        examples=[
            OpenApiExample(
                "Create Product Request",
                value={"name": "Air Max", "brand": "Nike", "price": "199.99", "discount_percentage": "10.00", "description": "Classic running shoe.", "category": 1, "sizes": [1, 2], "colors": [1], "tags": [1]},
                request_only=True,
            ),
            OpenApiExample(
                "Create Product Response",
                value={"status": True, "message": "Product created successfully", "data": {"id": 1, "name": "Air Max", "brand": "Nike", "price": "199.99", "is_active": True}},
                response_only=True, status_codes=["201"],
            ),
        ],
    )
    def create(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_product_service().create_product(serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ProductAdminReadSerializer(instance, context={"request": request}).data,
            message="Product created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="admin_product_retrieve",
        summary="Retrieve a product",
        responses={200: ProductAdminReadSerializer, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample(
                "Product Detail",
                value={"status": True, "message": "Product retrieved successfully", "data": {"id": 1, "name": "Air Max", "brand": "Nike", "price": "199.99", "is_active": True}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def retrieve(self, request, pk: int = None):
        try:
            instance = _get_product_service().get_product(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ProductAdminReadSerializer(instance, context={"request": request}).data,
            message="Product retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_product_update",
        summary="Partially update a product",
        request=ProductWriteSerializer,
        responses={200: ProductAdminReadSerializer, 400: {"description": "Validation error"}, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Update Product Request", value={"name": "Air Max Pro", "price": "249.99"}, request_only=True),
            OpenApiExample("Update Product Response", value={"status": True, "message": "Product updated successfully", "data": {"id": 1, "name": "Air Max Pro"}}, response_only=True, status_codes=["200"]),
        ],
    )
    def partial_update(self, request, pk: int = None):
        serializer = ProductWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_product_service().update_product(pk, serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ProductAdminReadSerializer(instance, context={"request": request}).data,
            message="Product updated successfully",
        )

    @extend_schema(
        operation_id="admin_product_delete",
        summary="Delete a product",
        responses={200: {"description": "Deleted"}},
        examples=[
            OpenApiExample("Delete Product", value={"status": True, "message": "Product deleted successfully", "data": None}, response_only=True, status_codes=["200"]),
        ],
    )
    def destroy(self, request, pk: int = None):
        try:
            _get_product_service().delete_product(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Product deleted successfully")

    @extend_schema(
        operation_id="admin_product_toggle_active",
        summary="Toggle product active status",
        request=None,
        responses={200: {"description": "Toggled"}},
        examples=[
            OpenApiExample("Toggle Active", value={"status": True, "message": "Product active status toggled successfully", "data": {"is_active": False}}, response_only=True, status_codes=["200"]),
        ],
    )
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk: int = None):
        try:
            is_active = _get_product_service().toggle_active_product(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(data={"is_active": is_active}, message="Product active status toggled successfully")


# ---------------------------------------------------------------------------
# Admin — Category
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Category"])
class AdminCategoryViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_category_list",
        summary="List all categories",
        parameters=[*PAGINATION_PARAMS],
        responses={200: CategoryAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample("Category List", value={"status": True, "message": "Categories retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "next_pages": None, "results": [{"id": 1, "name": "Running", "is_active": True}]}}, response_only=True, status_codes=["200"]),
        ],
    )
    def list(self, request):
        try:
            categories = _get_category_service().get_all_categories()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return _paginate(request, categories, CategoryAdminReadSerializer, "Categories retrieved successfully")

    @extend_schema(
        operation_id="admin_category_create",
        summary="Create a category",
        request=CategoryWriteSerializer,
        responses={201: CategoryAdminReadSerializer, 400: {"description": "Validation error"}},
        examples=[
            OpenApiExample("Create Category Request", value={"name": "Running", "is_active": True}, request_only=True),
            OpenApiExample("Create Category Response", value={"status": True, "message": "Category created successfully", "data": {"id": 1, "name": "Running", "is_active": True}}, response_only=True, status_codes=["201"]),
        ],
    )
    def create(self, request):
        serializer = CategoryWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_category_service().create_category(serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CategoryAdminReadSerializer(instance, context={"request": request}).data,
            message="Category created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="admin_category_retrieve",
        summary="Retrieve a category",
        responses={200: CategoryAdminReadSerializer, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Category Detail", value={"status": True, "message": "Category retrieved successfully", "data": {"id": 1, "name": "Running", "is_active": True}}, response_only=True, status_codes=["200"]),
        ],
    )
    def retrieve(self, request, pk: int = None):
        try:
            instance = _get_category_service().get_category(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CategoryAdminReadSerializer(instance, context={"request": request}).data,
            message="Category retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_category_update",
        summary="Partially update a category",
        request=CategoryWriteSerializer,
        responses={200: CategoryAdminReadSerializer, 400: {"description": "Validation error"}, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Update Category Request", value={"name": "Trail Running"}, request_only=True),
        ],
    )
    def partial_update(self, request, pk: int = None):
        serializer = CategoryWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_category_service().update_category(pk, serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CategoryAdminReadSerializer(instance, context={"request": request}).data,
            message="Category updated successfully",
        )

    @extend_schema(
        operation_id="admin_category_delete",
        summary="Delete a category",
        responses={200: {"description": "Deleted"}},
        examples=[
            OpenApiExample("Delete Category", value={"status": True, "message": "Category deleted successfully", "data": None}, response_only=True, status_codes=["200"]),
        ],
    )
    def destroy(self, request, pk: int = None):
        try:
            _get_category_service().delete_category(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Category deleted successfully")

    @extend_schema(
        operation_id="admin_category_toggle_active",
        summary="Toggle category active status",
        request=None,
        responses={200: {"description": "Toggled"}},
        examples=[
            OpenApiExample("Toggle Category Active", value={"status": True, "message": "Category active status toggled successfully", "data": {"is_active": False}}, response_only=True, status_codes=["200"]),
        ],
    )
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk: int = None):
        try:
            is_active = _get_category_service().toggle_active_category(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(data={"is_active": is_active}, message="Category active status toggled successfully")


# ---------------------------------------------------------------------------
# Admin — Tag
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Tag"])
class AdminTagViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_tag_list",
        summary="List all tags",
        parameters=[*PAGINATION_PARAMS],
        responses={200: TagAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample("Tag List", value={"status": True, "message": "Tags retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "next_pages": None, "results": [{"id": 1, "name": "Sport", "is_active": True}]}}, response_only=True, status_codes=["200"]),
        ],
    )
    def list(self, request):
        try:
            tags = _get_tag_service().get_all_tags()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return _paginate(request, tags, TagAdminReadSerializer, "Tags retrieved successfully")

    @extend_schema(
        operation_id="admin_tag_create",
        summary="Create a tag",
        request=TagWriteSerializer,
        responses={201: TagAdminReadSerializer, 400: {"description": "Validation error"}},
        examples=[
            OpenApiExample("Create Tag Request", value={"name": "Sport", "is_active": True}, request_only=True),
            OpenApiExample("Create Tag Response", value={"status": True, "message": "Tag created successfully", "data": {"id": 1, "name": "Sport", "is_active": True}}, response_only=True, status_codes=["201"]),
        ],
    )
    def create(self, request):
        serializer = TagWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_tag_service().create_tag(serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TagAdminReadSerializer(instance, context={"request": request}).data,
            message="Tag created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="admin_tag_retrieve",
        summary="Retrieve a tag",
        responses={200: TagAdminReadSerializer, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Tag Detail", value={"status": True, "message": "Tag retrieved successfully", "data": {"id": 1, "name": "Sport", "is_active": True}}, response_only=True, status_codes=["200"]),
        ],
    )
    def retrieve(self, request, pk: int = None):
        try:
            instance = _get_tag_service().get_tag(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TagAdminReadSerializer(instance, context={"request": request}).data,
            message="Tag retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_tag_update",
        summary="Partially update a tag",
        request=TagWriteSerializer,
        responses={200: TagAdminReadSerializer, 400: {"description": "Validation error"}, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Update Tag Request", value={"name": "Casual"}, request_only=True),
        ],
    )
    def partial_update(self, request, pk: int = None):
        serializer = TagWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_tag_service().update_tag(pk, serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TagAdminReadSerializer(instance, context={"request": request}).data,
            message="Tag updated successfully",
        )

    @extend_schema(
        operation_id="admin_tag_delete",
        summary="Delete a tag",
        responses={200: {"description": "Deleted"}},
        examples=[
            OpenApiExample("Delete Tag", value={"status": True, "message": "Tag deleted successfully", "data": None}, response_only=True, status_codes=["200"]),
        ],
    )
    def destroy(self, request, pk: int = None):
        try:
            _get_tag_service().delete_tag(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Tag deleted successfully")

    @extend_schema(
        operation_id="admin_tag_toggle_active",
        summary="Toggle tag active status",
        request=None,
        responses={200: {"description": "Toggled"}},
        examples=[
            OpenApiExample("Toggle Tag Active", value={"status": True, "message": "Tag active status toggled successfully", "data": {"is_active": False}}, response_only=True, status_codes=["200"]),
        ],
    )
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk: int = None):
        try:
            is_active = _get_tag_service().toggle_active_tag(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(data={"is_active": is_active}, message="Tag active status toggled successfully")


# ---------------------------------------------------------------------------
# Admin — Colour
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Colour"])
class AdminColourViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_colour_list",
        summary="List all colours",
        parameters=[*PAGINATION_PARAMS],
        responses={200: ColourAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample("Colour List", value={"status": True, "message": "Colours retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "next_pages": None, "results": [{"id": 1, "name": "Black"}]}}, response_only=True, status_codes=["200"]),
        ],
    )
    def list(self, request):
        try:
            colours = _get_colour_service().get_all_colours()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return _paginate(request, colours, ColourAdminReadSerializer, "Colours retrieved successfully")

    @extend_schema(
        operation_id="admin_colour_create",
        summary="Create a colour",
        request=ColourWriteSerializer,
        responses={201: ColourAdminReadSerializer, 400: {"description": "Validation error"}},
        examples=[
            OpenApiExample("Create Colour Request", value={"name": "Black"}, request_only=True),
            OpenApiExample("Create Colour Response", value={"status": True, "message": "Colour created successfully", "data": {"id": 1, "name": "Black"}}, response_only=True, status_codes=["201"]),
        ],
    )
    def create(self, request):
        serializer = ColourWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_colour_service().create_colour(serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ColourAdminReadSerializer(instance, context={"request": request}).data,
            message="Colour created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="admin_colour_retrieve",
        summary="Retrieve a colour",
        responses={200: ColourAdminReadSerializer, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Colour Detail", value={"status": True, "message": "Colour retrieved successfully", "data": {"id": 1, "name": "Black"}}, response_only=True, status_codes=["200"]),
        ],
    )
    def retrieve(self, request, pk: int = None):
        try:
            instance = _get_colour_service().get_colour(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ColourAdminReadSerializer(instance, context={"request": request}).data,
            message="Colour retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_colour_update",
        summary="Partially update a colour",
        request=ColourWriteSerializer,
        responses={200: ColourAdminReadSerializer, 400: {"description": "Validation error"}, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Update Colour Request", value={"name": "Navy Blue"}, request_only=True),
        ],
    )
    def partial_update(self, request, pk: int = None):
        serializer = ColourWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_colour_service().update_colour(pk, serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=ColourAdminReadSerializer(instance, context={"request": request}).data,
            message="Colour updated successfully",
        )

    @extend_schema(
        operation_id="admin_colour_delete",
        summary="Delete a colour",
        responses={200: {"description": "Deleted"}},
        examples=[
            OpenApiExample("Delete Colour", value={"status": True, "message": "Colour deleted successfully", "data": None}, response_only=True, status_codes=["200"]),
        ],
    )
    def destroy(self, request, pk: int = None):
        try:
            _get_colour_service().delete_colour(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Colour deleted successfully")


# ---------------------------------------------------------------------------
# Admin — Size
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Size"])
class AdminSizeViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_size_list",
        summary="List all sizes",
        parameters=[*PAGINATION_PARAMS],
        responses={200: SizeSerializer(many=True)},
        examples=[
            OpenApiExample("Size List", value={"status": True, "message": "Sizes retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "next_pages": None, "results": [{"id": 1, "name": "42"}]}}, response_only=True, status_codes=["200"]),
        ],
    )
    def list(self, request):
        try:
            sizes = _get_size_service().get_all_sizes()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return _paginate(request, sizes, SizeSerializer, "Sizes retrieved successfully")

    @extend_schema(
        operation_id="admin_size_create",
        summary="Create a size",
        request=SizeWriteSerializer,
        responses={201: SizeSerializer, 400: {"description": "Validation error"}},
        examples=[
            OpenApiExample("Create Size Request", value={"name": "42"}, request_only=True),
            OpenApiExample("Create Size Response", value={"status": True, "message": "Size created successfully", "data": {"id": 1, "name": "42"}}, response_only=True, status_codes=["201"]),
        ],
    )
    def create(self, request):
        serializer = SizeWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_size_service().create_size(serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=SizeSerializer(instance, context={"request": request}).data,
            message="Size created successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="admin_size_retrieve",
        summary="Retrieve a size",
        responses={200: SizeSerializer, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Size Detail", value={"status": True, "message": "Size retrieved successfully", "data": {"id": 1, "name": "42"}}, response_only=True, status_codes=["200"]),
        ],
    )
    def retrieve(self, request, pk: int = None):
        try:
            instance = _get_size_service().get_size(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=SizeSerializer(instance, context={"request": request}).data,
            message="Size retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_size_update",
        summary="Partially update a size",
        request=SizeWriteSerializer,
        responses={200: SizeSerializer, 400: {"description": "Validation error"}, 404: {"description": "Not found"}},
        examples=[
            OpenApiExample("Update Size Request", value={"name": "43"}, request_only=True),
        ],
    )
    def partial_update(self, request, pk: int = None):
        serializer = SizeWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = _get_size_service().update_size(pk, serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=SizeSerializer(instance, context={"request": request}).data,
            message="Size updated successfully",
        )

    @extend_schema(
        operation_id="admin_size_delete",
        summary="Delete a size",
        responses={200: {"description": "Deleted"}},
        examples=[
            OpenApiExample("Delete Size", value={"status": True, "message": "Size deleted successfully", "data": None}, response_only=True, status_codes=["200"]),
        ],
    )
    def destroy(self, request, pk: int = None):
        try:
            _get_size_service().delete_size(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Size deleted successfully")
