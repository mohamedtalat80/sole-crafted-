from rest_framework import viewsets, status, response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.decorators import action
from apps.contact_us.repositories.contact_repository import ContactMessageRepository, ContactContentRepository
from apps.contact_us.serializers import (
    ContactMessageReadSerializer,
    ContactMessageWriteSerializer,
    ContactContentReadSerializer,
    ContactContentWriteSerializer
)
from drf_spectacular.utils import extend_schema,OpenApiExample, OpenApiParameter

from apps.core.permissions import IsAdminAccount
from apps.core.responses import success_response, error_response
from apps.contact_us.services.contact_services import ContactMessageService, ContactContentService
from apps.core.exceptions import ApplicationError
from apps.core.utils.translation_utils import TranslationService, TRANSLATION_LANGUAGES
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError

def _get_contact_message_service():
    return ContactMessageService(ContactMessageRepository())
def _get_contact_content_service():
    return ContactContentService(ContactContentRepository(), TranslationService(api_key=getattr(settings, 'API_TRANSLATION_KEY', "")))  
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
@extend_schema(tags=["Contact Us Content"],)
class PublicContactContentListView(APIView):
    permission_classes = [AllowAny]  
    @extend_schema(
            operation_id="GetContactContent",
            summary="Get contact content",
            description="Retrieves the contact content including title, description, contact information, and social media links.",
            responses={200: ContactContentReadSerializer},
            examples=[
                OpenApiExample(
                    "Get Contact Content Response",
                    value={
                        "id": 1,
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "id": 1,
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "id": 1,
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "id": 2,
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "id": 2,
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                "id": 1,
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                "id": 2,
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                )
            ]
        )
    def get(self, request):
        service = _get_contact_content_service()
        content = service.get_contact_content()
        serializer = ContactContentReadSerializer(content, context={'request': request})
        return success_response(data=serializer.data)
    
@extend_schema(tags=["Admin — Contact Us Content"],)
class AdminContactContentView(APIView):
    permission_classes = [IsAdminAccount]  
    @extend_schema(
            operation_id="RetrieveContactContent",
            summary="Retrieve contact content",
            description="Retrieves the contact content including title, description, contact information, and social media links.",
            request=ContactContentWriteSerializer,
            responses={200: ContactContentReadSerializer},
            examples=[
                OpenApiExample(
                    "Retrieve Contact Content Response",
                    value={
                        "id": 1,
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "id": 1,
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "id": 1,
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "id": 2,
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "id": 2,
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                "id": 1,
                                "label": "Facebook",
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                "id": 2,
                                "label": "Twitter",
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                )

            ]
        )
    def get(self, request):
        service = _get_contact_content_service()
        content = service.get_contact_content()
        serializer = ContactContentReadSerializer(content, context={'request': request})
        return success_response(data=serializer.data)
    @extend_schema(
            operation_id="CreateContactContent",
            summary="Create contact content",
            description="Creates the contact content including title, description, contact information, and social media links.",    
            request=ContactContentWriteSerializer,
            responses={200: ContactContentReadSerializer},
            examples=[
                OpenApiExample(
                    "Create Contact Content Request",
                    value={
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        
                    }
                ),
                OpenApiExample(
                    "Create/Update Contact Content Response",
                    value={
                        "id": 1,
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "id": 1,
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "id": 1,
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "id": 2,
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "id": 2,
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                "id": 1,
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                "id": 2,
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                )
            ]
        )

    def post(self, request):
        service = _get_contact_content_service()
        serializer = ContactContentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            service.create_contact_content(serializer.validated_data)
            content = service.get_contact_content()
            serializer = ContactContentReadSerializer(content, context={'request': request})
            return success_response(data=serializer.data, message="Contact content created successfully.")
        except (ApplicationError, DjangoValidationError) as e:
            message = str(e) if isinstance(e, ApplicationError) else "Validation failed"
            return error_response(message=message, status_code=status.HTTP_400_BAD_REQUEST)
    @extend_schema(
            operation_id="UpdateContactContent",
            summary="Update contact content",
            description="Updates the contact content including title, description, contact information, and social media links.",
            request=ContactContentWriteSerializer,
            responses={200: ContactContentReadSerializer},
            examples=[
                OpenApiExample(
                    "Create/Update Contact Content Request",
                    value={
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                "label": "Facebook",
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                "label": "Twitter",
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                ),
                OpenApiExample(
                    "Create/Update Contact Content Response",
                    value={
                        "id": 1,
                        "title": "Contact Us",
                        "description": "Feel free to reach out to us through any of the following methods.",
                        "contact_infos": [
                            {
                                "id": 1,
                                "label": "Phone",
                                "value": "+1234567890",
                                "type": "phone",
                                "icon": {
                                    "id": 1,
                                    "name": "Phone Icon",
                                    "icon": "/media/icons/phone.png"
                                }
                            },
                            {
                                "id": 2,
                                "label": "Email",
                                "value": "info@o-marina.com",
                                "type": "email",
                                "icon": {
                                    "id": 2,
                                    "name": "Email Icon",
                                    "icon": "/media/icons/email.png"
                                }
                            }
                        ],
                        "social_links": [
                            {
                                "id": 1,
                                "label": "Facebook",
                                "url": "https://www.facebook.com/omarina",
                                "type": "facebook"
                            },
                            {
                                "id": 2,
                                "label": "Twitter",
                                "url": "https://www.twitter.com/omarina",
                                "type": "twitter"
                            }
                        ],
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                )
            ]
        )
    def patch(self, request):
        service = _get_contact_content_service()
        serializer = ContactContentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            service.update_contact_content(serializer.validated_data)
            content = service.get_contact_content()
            serializer = ContactContentReadSerializer(content, context={'request': request})
            return success_response(data=serializer.data, message="Contact content updated successfully.")
        except (ApplicationError, DjangoValidationError) as e:
            message = str(e) if isinstance(e, ApplicationError) else "Validation failed"
            return error_response(message=message, status_code=status.HTTP_400_BAD_REQUEST)
    @extend_schema(
            operation_id="DeleteContactContent",
            summary="Delete contact content",
            description="Deletes the contact content.",
            responses={200: None},
            examples=[
                OpenApiExample(
                    "Delete Contact Content Response",
                    value=None
                )
            ]
        )
    def delete(self, request):
        service = _get_contact_content_service()
        try:
            service.delete_contact_content()
            return success_response(message="Contact content deleted successfully.")
        except ApplicationError as e:
            return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as e:
            return error_response(message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST)
