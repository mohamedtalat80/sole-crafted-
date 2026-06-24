"""
Views for the FAQ app.

Admin endpoints  (/api/admin/FAQ/owner, /api/admin/FAQ/customer)
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
from apps.FAQ.repositories.faq_repository import FAQRepository
from apps.FAQ.serializers import FAQReadSerializer, FAQWriteSerializer, FAQToggleActiveSerializer
from apps.FAQ.services.faq_service import FAQService
from apps.core.utils.translation_utils import TranslationService
from django.conf import settings

def _get_FAQ_service() -> FAQService:
    return FAQService(repository=FAQRepository(),translation=TranslationService(api_key=settings.API_TRANSLATION_KEY))




@extend_schema(tags=["FAQ"])
class FAQListView(PaginationMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="FAQ_list",
        summary="List active FAQ",
        auth=[],
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: FAQReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Owner FAQ List Response",
                value={"status": True, "message": "FAQS retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {"id": 1, "question": "How do I list my boat?", "answer": "Go to your dashboard and click 'Add Boat'.", "display_order": 1},
                    {"id": 2, "question": "How do I manage bookings?", "answer": "Visit the Bookings section in your dashboard.", "display_order": 2},
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            service = _get_FAQ_service()
            faqs = service.get_all_active_FAQS
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(faqs, FAQReadSerializer, request, "FAQS retrieved successfully")


# ---------------------------------------------------------------------------
# Admin FAQs: list + create
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — FAQ"])
class AdminFAQListView(PaginationMixin, APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_FAQ_service()

    @extend_schema(
        operation_id="admin_FAQ_list",
        summary="List FAQs",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: FAQReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Admin FAQ List Response",
                value={"status": True, "message": "FAQS retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {"id": 1, "question": "How do I list my boat?", "answer": "Go to your dashboard.", "display_order": 1, "is_active": True},
                    {"id": 2, "question": "How do I manage bookings?", "answer": "Visit Bookings section.", "display_order": 2, "is_active": False},
                ]}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            faqs = self.service.get_all_FAQS()
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return self.paginate_and_respond(faqs, FAQReadSerializer, request, "FAQS retrieved successfully")

    @extend_schema(
        operation_id="admin_FAQ_create",
        summary="Create FAQ",
        request=FAQWriteSerializer,
        responses={201: FAQReadSerializer, 400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Create owner FAQ",
                value={"question": "How do I list my boat?", "answer": "Go to your dashboard and click 'Add Boat'.", "display_order": 1},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = FAQWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            faq = self.service.add_FAQ(data=request.data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=FAQReadSerializer(faq, context={"request": request}).data,
            message="FAQ created successfully",
        )


# ---------------------------------------------------------------------------
# Admin FAQs: retrieve, update, delete
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin — FAQ"])
class AdminFAQView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_FAQ_service()

    @extend_schema(
        operation_id="admin_FAQ_retrieve",
        summary="Retrieve FAQ",
        parameters=[_ACCEPT_LANGUAGE_PARAM],
        responses={200: FAQReadSerializer},
        examples=[
            OpenApiExample(
                "Admin FAQ Retrieve Response",
                value={"status": True, "message": "FAQ retrieved successfully", "data": {"id": 1, "question": "How do I list my boat?", "answer": "Go to your dashboard.", "display_order": 1, "is_active": True}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def get(self, request, pk: int):
        try:
            faq = self.service.get_FAQ_by_id(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=FAQReadSerializer(faq, context={"request": request}).data,
            message="FAQ retrieved successfully",
        )
    @extend_schema(
        operation_id="admin_FAQ_update",
        summary="Update FAQ",
        request=FAQWriteSerializer,
        responses={200: FAQReadSerializer,400: {"description": "Invalid data"}},
        examples=[
            OpenApiExample(
                "Update FAQ",
                value={"question": "How do I update my boat listing?", "answer": "Edit your boat details from the dashboard.", "display_order": 2},
                request_only=True,
            )
        ],
    )
    def patch(self, request, pk: int):
        serializer = FAQWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                message="Invalid data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            faq = self.service.update_FAQ(pk, request.data)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=FAQReadSerializer(faq, context={"request": request}).data,
            message="FAQ updated successfully",
        )
    @extend_schema(
        operation_id="admin_FAQ_delete",
        summary="Delete FAQ",
        responses={200: {"description": "FAQ deleted successfully"}},
        examples=[
            OpenApiExample(
                "Delete FAQ Response",
                value={"status": True, "message": "FAQ deleted successfully", "data": None},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def delete(self, request, pk: int):
        try:
            self.service.delete_FAQ(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(message="FAQ deleted successfully")


@extend_schema(tags=["Admin — FAQ"])
class AdminFAQToggleActiveView(APIView):
    permission_classes = [IsAdminAccount]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = _get_FAQ_service()

    @extend_schema(
        operation_id="admin_FAQ_toggle_active",
        summary="Toggle active status of FAQ",
        request=None,
        responses={200: FAQToggleActiveSerializer},
        examples=[
            OpenApiExample(
                "Toggle FAQ Active Response",
                value={"status": True, "message": "FAQ active status toggled successfully", "data": {"is_active": False}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            faq = self.service.toggle_active_FAQ(pk)
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=FAQToggleActiveSerializer(faq).data,
            message="FAQ active status toggled successfully",
        )


