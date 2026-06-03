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
from django.conf import settings

from apps.core.exceptions import ApplicationError
from apps.core.pagination import PaginationMixin
from apps.core.permissions import IsAdminAccount
from apps.core.responses import error_response, success_response
from apps.core.utils.translation_utils import TranslationService
from apps.privacy_policy.repositories.privacy_policy_repository import PrivacyPolicyRepository
from apps.privacy_policy.serializers import (
    PrivacyPolicyReadSerializer,
    PrivacyPolicyWriteSerializer,
    PrivacyPolicyAdminReadSerializer,
)
from apps.privacy_policy.services.privacy_policy_service import PrivacyPolicyService


def _get_privacy_policy_service() -> PrivacyPolicyService:
    return PrivacyPolicyService(
        repository=PrivacyPolicyRepository(),
        translation=TranslationService(api_key=settings.API_TRANSLATION_KEY),
    )


# ---------------------------------------------------------------------------
# Public: list active privacy policies
# ---------------------------------------------------------------------------

@extend_schema(tags=["Privacy Policy"])
class PrivacyPolicyView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="privacy_policy_list",
        summary="List active privacy policies",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: PrivacyPolicyReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Privacy Policy List Response",
                value={"status": True, "message": "Privacy policies retrieved successfully", "data": {"count": 1, "next": None, "previous": None, "results": [
                    {"id": 1, "title": "We respect your privacy.", "content": "We respect your privacy and protect your data.", "display_order": 1, "is_active": True},
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            service = _get_privacy_policy_service()
            policies = service.get_all_active_privacy_policies()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(policies, PrivacyPolicyReadSerializer, request, "Privacy policies retrieved successfully")


# ---------------------------------------------------------------------------
# Admin: list + create
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Privacy Policy"])
class AdminPrivacyPolicyListCreateView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_privacy_policy_service()

    @extend_schema(
        operation_id="admin_privacy_policy_list",
        summary="List all privacy policies",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: PrivacyPolicyAdminReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Admin Privacy Policy List Response",
                value={"status": True, "message": "Privacy policies retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {"id": 1, "title": "We respect your privacy.", "content": "We respect your privacy.", "display_order": 1, "updated_by": None, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
                    {"id": 2, "title": "Previous privacy policy.", "content": "Previous privacy policy.", "display_order": 2, "updated_by": None, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            policies = self.service.get_all_privacy_policies()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(policies, PrivacyPolicyAdminReadSerializer, request, "Privacy policies retrieved successfully")

    @extend_schema(
        operation_id="admin_privacy_policy_create",
        summary="Create privacy policy",
        request=PrivacyPolicyWriteSerializer,
        responses={201: PrivacyPolicyAdminReadSerializer, 400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Create Privacy Policy",
                value={"title": "We respect your privacy.", "content": "We respect your privacy and protect your data.", "display_order": 1},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PrivacyPolicyWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = self.service.add_privacy_policy(data=serializer.validated_data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=PrivacyPolicyAdminReadSerializer(instance, context={"request": request}).data,
            message="Privacy policy created successfully",
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin: retrieve, update, delete
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Privacy Policy"])
class AdminPrivacyPolicyView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_privacy_policy_service()

    @extend_schema(
        operation_id="admin_privacy_policy_retrieve",
        summary="Retrieve privacy policy",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: PrivacyPolicyAdminReadSerializer},
    )
    def get(self, request, pk: int):
        try:
            instance = self.service.get_privacy_policy_by_id(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=PrivacyPolicyAdminReadSerializer(instance, context={"request": request}).data,
            message="Privacy policy retrieved successfully",
        )

    @extend_schema(
        operation_id="admin_privacy_policy_update",
        summary="Update privacy policy",
        request=PrivacyPolicyWriteSerializer,
        responses={200: PrivacyPolicyAdminReadSerializer, 400: {"description": "Invalid data"}},
    )
    def patch(self, request, pk: int):
        serializer = PrivacyPolicyWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            instance = self.service.update_privacy_policy(pk, serializer.validated_data, updated_by=request.user)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=PrivacyPolicyAdminReadSerializer(instance, context={"request": request}).data,
            message="Privacy policy updated successfully",
        )

    @extend_schema(
        operation_id="admin_privacy_policy_delete",
        summary="Delete privacy policy",
        responses={200: {"description": "Privacy policy deleted successfully"}},
    )
    def delete(self, request, pk: int):
        try:
            self.service.delete_privacy_policy(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="Privacy policy deleted successfully")


# ---------------------------------------------------------------------------
# Admin: toggle active
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — Privacy Policy"])
class AdminPrivacyPolicyToggleActiveView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_privacy_policy_service()

    @extend_schema(
        operation_id="admin_privacy_policy_toggle_active",
        summary="Toggle active status of privacy policy",
        request=None,
        responses={200: {"description": "Active status toggled"}},
        examples=[
            OpenApiExample(
                "Toggle Privacy Policy Active",
                value={"status": True, "message": "Privacy policy active status toggled successfully", "data": {"is_active": False}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            is_active = self.service.toggle_active_privacy_policy(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(data={"is_active": is_active}, message="Privacy policy active status toggled successfully")
