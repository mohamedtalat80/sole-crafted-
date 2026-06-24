
from django.conf import settings
from apps.contact_us.repositories.contact_repository import ContactMessageRepository
from apps.core.email import send_email
from apps.core.exceptions import NotFoundError
import logging
logger = logging.getLogger(__name__)

from apps.contact_us.utils import send_contact_email

class ContactMessageService:
    def __init__(self, repository=None):
        self.repository = repository or ContactMessageRepository()

    def get_all_contact_messages(self):
        return self.repository.get_all_contact_messages()

    def get_contact_message_by_id(self, id: int):
        return self.repository.get_contact_message_by_id(id)

    def create_contact_message(self, data: dict):
        # Save the message first to ensure image is stored and we have access to its URL
        contact_message = self.repository.create_contact_message(data)

        # Send email notification asynchronously or in-flow
        send_contact_email(contact_message)

        return contact_message

    def delete_contact_message(self, id: int):
        return self.repository.delete_contact_message(id)


