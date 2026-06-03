
from django.conf import settings
from apps.contact_us.repositories.contact_repository import ContactMessageRepository, ContactContentRepository
from apps.core.email import send_email
from apps.core.utils.translation_utils import TranslationService, TRANSLATION_LANGUAGES
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


class ContactContentService:
    def __init__(self, repository=None, translation_service=None):
        self.repository = repository or ContactContentRepository()
        self.translation_service = translation_service or TranslationService(api_key=getattr(settings, 'API_TRANSLATION_KEY', ""))

    def get_contact_content(self):
        content = self.repository.get_contact_content()
        if not content:
            raise NotFoundError("Contact content not found.")
        return content

    def create_contact_content(self, data: dict):
        content = self.repository.create_contact_content(data)
        self._auto_translate_all(content)
        return content

    def update_contact_content(self, data: dict):
        content = self.repository.update_contact_content(data)
        self._auto_translate_all(content)
        return content

    def delete_contact_content(self) -> bool:
        if not self.repository.delete_contact_content():
            raise NotFoundError("Contact content not found.")
        return True

    def _auto_translate_all(self,ContactContent) -> None:
        source = {"title": ContactContent.title, "description": ContactContent.description}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self.translation_service.translate_batch(source, lang_name)
                self.repository.upsert_contact_content_translation(
                    ContactContent, lang_code,
                    translated.get("title", ContactContent.title),
                    translated.get("description", ContactContent.description)
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("Failed to translate contact content %s to %s", ContactContent.pk, lang_code)
