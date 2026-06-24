from typing import Optional
from apps.contact_us.interfaces.contact_repository_interface import IContactMessage
from apps.contact_us.models import ContactMessage
from apps.core.exceptions import NotFoundError
from django.db import transaction


class ContactMessageRepository(IContactMessage):
    def get_all_contact_messages(self):
        return ContactMessage.objects.all()
    def get_contact_message_by_id(self, id: int) -> ContactMessage:
        try:
            message = ContactMessage.objects.get(id=id)
        except ContactMessage.DoesNotExist:
            raise NotFoundError(f"Contact message with id {id} not found.")
        return message
    def create_contact_message(self, data: dict) -> ContactMessage:
        full_name = data.get('full_name')
        email = data.get('email')
        message = data.get('message')
        subject = data.get('subject')
        
        if data.get('phone'):
            phone = data.get('phone')
        else:            
            phone = None
        if data.get('image'):
            image = data.get('image')
        else:
            image = None
        contact_message = ContactMessage.objects.create(
            full_name=full_name,
            email=email,
            message=message,
            subject=subject,
            phone=phone,
            image=image
        )
        return contact_message
    def delete_contact_message(self, id: int) -> bool:
        contact_message = self.get_contact_message_by_id(id)
        contact_message.delete()
        return True

