"""
Views for the CookiesPolicy app.

Owner endpoint  (/api/CookiesPolicy/owner)
customer endpoint  (/api/CookiesPolicy/customer)
Admin endpoints  (/api/admin/CookiesPolicy/owner, /api/admin/CookiesPolicy/customer)
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
from apps.cookies_policy.repositories.cookies_policy_repository import CookiesPolicyRepository
from apps.cookies_policy.serializers import CookiesPolicyReadSerializer, CookiesPolicyWriteSerializer,CookiesPolicyAdminReadSerializer
from apps.cookies_policy.services.cookies_policy_service import CookiesPolicyService
from apps.core.utils.translation_utils import TranslationService
from django.conf import settings

def _get_CookiesPolicy_service() -> CookiesPolicyService:
    return CookiesPolicyService(repository=CookiesPolicyRepository(),translation=TranslationService(api_key=settings.API_TRANSLATION_KEY))


# ---------------------------------------------------------------------------
# CookiesPolicy — list
# ---------------------------------------------------------------------------

@extend_schema(tags=["CookiesPolicy"])
class CookiesPolicyView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="CookiesPolicy_list",
        summary="List Active CookiesPolicy",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: CookiesPolicyReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Cookies Policy List Response",
                value={"status": True, "message": "CookiesPolicys retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "results": [
                    {
                        "id": 1, 
                        "title": "We respect your privacy and protect your data.",
                        "content": "We respect your privacy and protect your data.",
                        "display_order": 1,
                        "is_active": True,
                        "created_at": "2022-01-01T00:00:00Z",
                        "updated_at": "2022-01-01T00:00:00Z",
                        
                        }
                    
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            service = _get_CookiesPolicy_service()
            cookies_policies = service.get_all_active_privacy_policies()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(cookies_policies, CookiesPolicyReadSerializer, request, "CookiesPolicys retrieved successfully")

# ---------------------------------------------------------------------------
# Admin owner's CookiesPolicys: list + create
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — CookiesPolicy"])
class AdminCookiesPolicyListCreateView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_CookiesPolicy_service()

    @extend_schema(
        operation_id="admin_CookiesPolicy_list",
        summary="List All CookiesPolicys",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: CookiesPolicyAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Admin Cookies Policy List Response",
                value={"status": True, "message": "CookiesPolicyS retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {
                        "id": 1, 
                        "title": "We respect your privacy.", 
                        "content": "We respect your privacy.", 
                        "display_order": 1,
                        "is_active": True,
                        "created_at": "2022-01-01T00:00:00Z",
                        "updated_at": "2022-01-01T00:00:00Z",
                        },
                    {
                        "id": 2, 
                        "title": "Previous cookies policy.", 
                        "content": "Previous cookies policy.", 
                        "display_order": 2,
                        "is_active": False,
                        "created_at": "2022-01-01T00:00:00Z",
                        "updated_at": "2022-01-01T00:00:00Z",
                        },
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            cookies_policies = self.service.get_all_privacy_policies()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(cookies_policies, CookiesPolicyReadSerializer, request, "CookiesPolicyS retrieved successfully")

    @extend_schema(
        operation_id="admin_CookiesPolicy_create",
        summary="Create CookiesPolicy",
        request=CookiesPolicyWriteSerializer,
        responses={201: CookiesPolicyReadSerializer, 400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Create Cookies Policy Example",
                value={
                    "title": "This is our cookies policy...",
                    "content": "This is our cookies policy...",
                    "display_order": 1,
                    "is_active": True
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        serializer = CookiesPolicyWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cookies_policy = self.service.add_cookies_policy(data=request.data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CookiesPolicyReadSerializer(cookies_policy, context={"request": request}).data,
            message="CookiesPolicy created successfully",
        )


# ---------------------------------------------------------------------------
# Admin CookiesPolicys: retrieve, update, delete
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — CookiesPolicy"])
class AdminCookiesPolicyView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_CookiesPolicy_service()

    @extend_schema(
        operation_id="admin_CookiesPolicy_retrieve",
        summary="Retrieve CookiesPolicy",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: CookiesPolicyReadSerializer},
        examples=[
            OpenApiExample(
                "Admin Cookies Policy Retrieve Response",
                value={
                    "status": True, 
                    "message": "CookiesPolicy retrieved successfully",
                    "data": 
                    {"id": 1, 
                    "title": "We respect your privacy.", 
                    "content": "We respect your privacy.", 
                "display_order": 1, 
                "is_active": True,
                "created_at": "2022-01-01T00:00:00Z",
                "updated_at": "2022-01-01T00:00:00Z",
                }},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request, pk: int):
        try:
            cookies_policy = self.service.get_cookies_policy_by_id(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CookiesPolicyReadSerializer(cookies_policy, context={"request": request}).data,
            message="CookiesPolicy retrieved successfully",
        )
    @extend_schema(
        operation_id="admin_owner_CookiesPolicy_update",
        summary="Update owner's CookiesPolicy",
        request=CookiesPolicyWriteSerializer,
        responses={200: CookiesPolicyReadSerializer,400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Update Cookies Policy Example",
                value={
                    "title": "Updated cookies policy...",
                    "content": "Updated cookies policy...",
                    "display_order": 1,
                    "is_active": False
                },
                request_only=True
            )
        ]
    )
    def patch(self, request, pk: int):
        updated_by = request.user
        serializer = CookiesPolicyWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cookies_policy = self.service.update_cookies_policy(pk, request.data, updated_by)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=CookiesPolicyReadSerializer(cookies_policy, context={"request": request}).data,
            message="CookiesPolicy updated successfully",
        )
    @extend_schema(
        operation_id="admin_CookiesPolicy_delete",
        summary="Delete CookiesPolicy",
        responses={200: {"description": "Privacy policy deleted successfully"}},
        examples=[
            OpenApiExample(
                "Delete Cookies Policy Response",
                value={"status": True, "message": "Privacy policy deleted successfully", "data": None},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def delete(self, request, pk: int):
        try:
            self.service.delete_cookies_policy(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Privacy policy deleted successfully")


@extend_schema(tags=["Admin — CookiesPolicy"])
class AdminCookiesPolicyToggleActiveView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_CookiesPolicy_service()

    @extend_schema(
        operation_id="admin_CookiesPolicy_toggle_active",
        summary="Toggle active status of CookiesPolicy",
        request=None,
        responses={200: CookiesPolicyReadSerializer},
        examples=[
            OpenApiExample(
                "Toggle Cookies Policy Active Response",
                value={"status": True, "message": "CookiesPolicy active status toggled successfully", "data": {"id": 1, "text": "We respect your privacy.", "is_active": False}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            is_active = self.service.toggle_active_cookies_policy(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data={
                "is_active":is_active
            },
            message="CookiesPolicy active status toggled successfully",
        )

