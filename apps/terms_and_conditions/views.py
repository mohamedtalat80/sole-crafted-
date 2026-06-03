"""
Views for the TermsAndConditions app.

Owner endpoint  (/api/TermsAndConditions/owner)
customer endpoint  (/api/TermsAndConditions/customer)
Admin endpoints  (/api/admin/TermsAndConditions/owner, /api/admin/TermsAndConditions/customer)
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

_ACCEPT_LANGUAGE_PARAM = OpenApiParameter(
    name="Accept-Language",
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Language for the response content. "
        "Accepted values: `en` (default), `ar`, `nl`, `ru`, `pt`, `fr`, `de`, `hi`, `ko`, `es`. "
        "Falls back to English when a translation is unavailable."
    ),
    enum=["en", "ar", "nl", "ru", "pt", "fr", "de", "hi", "ko", "es"],
    default="en",
)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.core.exceptions import ApplicationError
from apps.core.pagination import PaginationMixin
from apps.core.permissions import IsAdminAccount
from apps.core.responses import error_response, success_response
from apps.terms_and_conditions.repositories.terms_and_conditions_repository import TermsAndConditionsRepository
from apps.terms_and_conditions.serializers import TermsAndConditionsReadSerializer, TermsAndConditionsWriteSerializer,TermsAndConditionsAdminReadSerializer
from apps.terms_and_conditions.services.terms_and_conditions_service import TermsAndConditionsService
from apps.core.utils.translation_utils import TranslationService
from django.conf import settings

def _get_TermsAndConditions_service() -> TermsAndConditionsService:
    return TermsAndConditionsService(repository=TermsAndConditionsRepository(),translation=TranslationService(api_key=settings.API_TRANSLATION_KEY))


# ---------------------------------------------------------------------------
# TermsAndConditions — list
# ---------------------------------------------------------------------------

@extend_schema(tags=["TermsAndConditions"])
class TermsAndConditionsView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="TermsAndConditions_list",
        summary="List active TermsAndConditions",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: TermsAndConditionsReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Terms and Conditions List Response",
                value={"status": True, "message": "TermsAndConditionss retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "results": [
                    {
                        "id": 1,
                        "title": "By using this service you agree to our terms.",
                        "content": "These are the terms and conditions...",
                        "display_order": 1,
                        "is_active": True,
                        "created_at": "2026-01-01T10:00:00Z",
                        "updated_at": "2026-01-01T10:00:00Z",
                    },
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    
    def get(self, request):
        try:
            service = _get_TermsAndConditions_service()
            TermsAndConditionss = service.get_all_active_terms_and_conditions()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(TermsAndConditionss, TermsAndConditionsReadSerializer, request, "TermsAndConditionss retrieved successfully")

# ---------------------------------------------------------------------------
# Admin owner's TermsAndConditionss: list + create
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — TermsAndConditions"])
class AdminTermsAndConditionsListCreateView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_TermsAndConditions_service()

    @extend_schema(
        operation_id="admin_TermsAndConditions_list",
        summary="List TermsAndConditionss",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: TermsAndConditionsAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Admin T&C List Response",
                value={"status": True, "message": "TermsAndConditionsS retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {"id": 1, "title": "By using this service you agree to our terms.", "content": "Terms content here...", "display_order": 1, "updated_by": None, "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:00:00Z"},
                    {"id": 2, "title": "Previous terms.", "content": "Previous content...", "display_order": 2, "updated_by": None, "created_at": "2025-12-01T10:00:00Z", "updated_at": "2025-12-01T10:00:00Z"},
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            TermsAndConditionss = self.service.get_all_terms_and_conditions()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(TermsAndConditionss, TermsAndConditionsAdminReadSerializer, request, "TermsAndConditionsS retrieved successfully")

    @extend_schema(
        operation_id="admin_TermsAndConditions_create",
        summary="Create TermsAndConditions",
        request=TermsAndConditionsWriteSerializer,
        responses={201: TermsAndConditionsReadSerializer, 400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Create T&C Example",
                value={
                    "title": "Terms and Conditions Title",
                    "content": "These are the terms and conditions...",
                    "display_order": 1
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        serializer = TermsAndConditionsWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            TermsAndConditions = self.service.add_TermsAndConditions(data=request.data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TermsAndConditionsAdminReadSerializer(TermsAndConditions, context={"request": request}).data,
            message="TermsAndConditions created successfully",
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin TermsAndConditionss: retrieve, update, delete
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — TermsAndConditions"])
class AdminTermsAndConditionsView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_TermsAndConditions_service()

    @extend_schema(
        operation_id="admin_TermsAndConditions_retrieve",
        summary="Retrieve TermsAndConditions",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: TermsAndConditionsAdminReadSerializer},
        examples=[
            OpenApiExample(
                "Admin T&C Retrieve Response",
                value={"status": True, "message": "TermsAndConditions retrieved successfully", "data": {"id": 1, "title": "By using this service you agree to our terms.", "content": "Terms content here...", "display_order": 1, "is_active": True, "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:00:00Z"}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request, pk: int):
        try:
            TermsAndConditions = self.service.get_TermsAndConditions_by_id(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TermsAndConditionsAdminReadSerializer(TermsAndConditions, context={"request": request}).data,
            message="TermsAndConditions retrieved successfully",
        )
    @extend_schema(
        operation_id="admin_owner_TermsAndConditions_update",
        summary="Update owner's TermsAndConditions",
        request=TermsAndConditionsWriteSerializer,
        responses={200: TermsAndConditionsReadSerializer,400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Update T&C Example",
                value={
                    "title": "Updated Terms Title",
                    "content": "Updated terms and conditions...",
                    "display_order": 2
                },
                request_only=True
            )
        ]
    )
    def patch(self, request, pk: int):
        updated_by = request.user
        serializer = TermsAndConditionsWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            TermsAndConditions = self.service.update_TermsAndConditions(pk, request.data,updated_by)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TermsAndConditionsAdminReadSerializer(TermsAndConditions, context={"request": request}).data,
            message="TermsAndConditions updated successfully",
        )
    @extend_schema(
        operation_id="admin_TermsAndConditions_delete",
        summary="Delete TermsAndConditions",
        responses={200: {"description": "Terms and conditions deleted successfully"}},
        examples=[
            OpenApiExample(
                "Delete T&C Response",
                value={"status": True, "message": "Terms and conditions deleted successfully", "data": None},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def delete(self, request, pk: int):
        try:
            self.service.delete_TermsAndConditions(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Terms and conditions deleted successfully")


@extend_schema(tags=["Admin — TermsAndConditions"])
class AdminTermsAndConditionsToggleActiveView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_TermsAndConditions_service()

    @extend_schema(
        operation_id="admin_TermsAndConditions_toggle_active",
        summary="Toggle active status of TermsAndConditions",
        request=None,
        responses={200: TermsAndConditionsAdminReadSerializer},
        examples=[
            OpenApiExample(
                "Toggle T&C Active Response",
                value={"status": True, "message": "TermsAndConditions active status toggled successfully", "data": {"id": 1, "title": "By using this service you agree to our terms.", "content": "Terms content here...", "display_order": 1, "is_active": False, "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:00:00Z"}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            TermsAndConditions = self.service.toggle_active_TermsAndConditions(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=TermsAndConditionsAdminReadSerializer(TermsAndConditions, context={"request": request}).data,
            message="TermsAndConditions active status toggled successfully",
        )

