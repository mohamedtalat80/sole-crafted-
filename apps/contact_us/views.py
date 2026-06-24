from rest_framework import viewsets, status, response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.decorators import action
from apps.contact_us.repositories.contact_repository import ContactMessageRepository
from apps.contact_us.serializers import (
    ContactMessageReadSerializer,
    ContactMessageWriteSerializer,
    
)
from drf_spectacular.utils import extend_schema,OpenApiExample, OpenApiParameter

from apps.core.permissions import IsAdminAccount
from apps.core.responses import success_response, error_response
from apps.contact_us.services.contact_services import ContactMessageService
from apps.core.exceptions import ApplicationError

def _get_contact_message_service():
    return ContactMessageService(ContactMessageRepository())
@extend_schema(tags=["Contact Us"],)
class UserContactMessageView(APIView):
    permission_classes = [AllowAny]  
    @extend_schema(
            operation_id="CreateContactUsMessage",
            summary="Submit a contact message",
            description="Allows users to submit a contact message with their name, email, subject, phone number, message content, and an optional image.",
            request=ContactMessageWriteSerializer,
            responses={200: ContactMessageReadSerializer},
            examples=[
                OpenApiExample(
                    "Create Contact Message Request",
                    value={
                        "full_name": "John Doe",
                        "email": "john.doe@example.com",
                        "subject": "general",
                        "phone": "+1234567890",
                        "message": "I have a question about your services.",
                        "image": None
                    },
                    request_only=True
                ),
                OpenApiExample(
                    "Create Contact Message Response",
                    value=None,
                    request_only=True
                )
            ]
        )

    def post(self, request):
        service = _get_contact_message_service()
        serializer = ContactMessageWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            contact_message = service.create_contact_message(serializer.validated_data)
            serializer = ContactMessageReadSerializer(contact_message, context={'request': request})
            return success_response(data=serializer.data, message="Contact message created successfully.")
        except ApplicationError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
@extend_schema(tags=["Admin — Contact Us"],)
class AdminContactMessageListView(APIView):

    permission_classes = [IsAdminAccount]
    @extend_schema(
            operation_id="ListContactMessages",
            summary="List all contact messages",
            description="Retrieves a list of all contact messages submitted by users.",
            responses={200: ContactMessageReadSerializer(many=True)},
            examples=[
                OpenApiExample(
                    "Get All Contact Messages Response",
                    value=[
                        {
                            "id": 1,
                            "full_name": "John Doe",
                            "email": "john.doe@example.com",
                            "subject": "general",
                            "phone": "+1234567890",
                            "message": "I have a question about your services.",
                            "image": None
                        },
                        {
                            "id": 2,
                            "full_name": "Jane Smith",
                            "email": "jane.smith@example.com",
                            "subject": "support",
                            "phone": "+0987654321",
                            "message": "I need help with my account.",
                            "image": None
                        }
                    ]
                )
            ]
        )
    def get(self, request):
        service = _get_contact_message_service()
        messages = service.get_all_contact_messages()
        serializer = ContactMessageReadSerializer(messages, many=True, context={'request': request})
        return success_response(data=serializer.data)
    
    
@extend_schema(tags=["Admin — Contact Us"],)
class AdminContactMessageDetailView(APIView):

    permission_classes = [IsAdminAccount]
    @extend_schema(
            operation_id="GetContactMessage",
            summary="Get a specific contact message",
            description="Retrieves the details of a specific contact message by its ID.",

            parameters=[
                OpenApiParameter(
                    name="id",
                    description="ID of the contact message",
                    required=True,
                    type=int
                )
            ],
            responses={200: ContactMessageReadSerializer},
            examples=[
                OpenApiExample(
                    "Get Contact Message Response",
                    value={
                        "id": 1,
                        "full_name": "John Doe",
                        "email": "john.doe@example.com",
                        "subject": "general",
                        "phone": "+1234567890",
                        "message": "I have a question about your services.",
                        "image": None
                    }
                )
            ]
        )

    def get(self, request, id):
        service = _get_contact_message_service()
        try:
            message = service.get_contact_message_by_id(id)
            serializer = ContactMessageReadSerializer(message, context={'request': request})
            return success_response(data=serializer.data)
        except ApplicationError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
    @extend_schema(
            operation_id="DeleteContactMessage",
            summary="Delete a specific contact message",
            description="Deletes a specific contact message by its ID.",
            parameters=[
                OpenApiParameter(
                    name="id",
                    description="ID of the contact message to delete",
                    required=True,
                    type=int
                )
            ],
            responses={200: None},
            examples=[
                OpenApiExample(
                    "Delete Contact Message Response",
                    value=None
                )
            ]
        )
    def delete(self, request, id):
        service = _get_contact_message_service()
        try:
            service.delete_contact_message(id)
            return success_response(message="Contact message deleted successfully.")
        except ApplicationError as e:
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

