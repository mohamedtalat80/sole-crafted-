from typing import Optional
from apps.contact_us.interfaces.contact_repository_interface import IContactMessage
from apps.contact_us.models import (
    ContactContentTranslation, 
    ContactMessage, 
    ContactContent, 
    ContactInfo, 
    ContactIcon,
    SocialMediaLink
)
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


class ContactContentRepository:
    def get_contact_content(self):
        contact_content = ContactContent.objects.prefetch_related(
            'contact_infos', 
            'contact_infos__icons', 
            'social_links',
            'translations'
        ).first()
        if not contact_content:
            return None
        return contact_content

    def _create_contact_icon(self,contact_info: ContactInfo, data: dict) -> ContactIcon:
        return ContactIcon.objects.create(
            contact_info=contact_info,
            name=data.get('name'),
            icon=data.get('icon')
        )

    def _create_contact_info(self, contact_content: ContactContent, data: dict) -> ContactInfo:

        contact_info= ContactInfo.objects.create(
            contact=contact_content,
            label=data.get('label'),
            value=data.get('value'),
            type=data.get('type'),
        )
        icons_data = data.get('icon', [])
        for icon_item in icons_data:
            self._create_contact_icon(contact_info, icon_item)
        return contact_info

    def _create_social_link(self, contact_content: ContactContent, data: dict) -> SocialMediaLink:
       url= data.get('url')
       type= data.get('type')
       return SocialMediaLink.objects.create(
            contact=contact_content,
            url=url,
            type=type
        )

    @transaction.atomic
    def create_contact_content(self, data: dict) -> ContactContent:
        title = data.get('title')
        description = data.get('description')
        contact_content = ContactContent.objects.create(title=title, description=description)

        contact_infos_data = data.get('contact_infos', [])
        for info_data in contact_infos_data:
            self._create_contact_info(contact_content, info_data)

        social_links_data = data.get('social_links', [])
        for link_data in social_links_data:
            self._create_social_link(contact_content, link_data)

        return contact_content
    def _update_social_links(self, contact_content: ContactContent, data: list) -> None:
        sent_ids = []
        for link_data in data:
            link_id = link_data.get("id")
            obj, _ = SocialMediaLink.objects.update_or_create(
                id=link_id if link_id else None,
                defaults={
                    "contact": contact_content,
                    "url": link_data.get("url"),
                    "type": link_data.get("type"),
                }
            )
            sent_ids.append(obj.id)
        
        SocialMediaLink.objects.filter(contact=contact_content).exclude(id__in=sent_ids).delete()

    def _update_contact_icons(self, contact_info: ContactInfo, data: list) -> None:
        sent_ids = []
        for icon_data in data:
            icon_id = icon_data.get("id")
            update_defaults = {
                "name": icon_data.get("name"),
                "contact_info": contact_info
            }
            if icon_data.get("icon"):
                update_defaults["icon"] = icon_data.get("icon")

            obj, _ = ContactIcon.objects.update_or_create(
                id=icon_id if icon_id else None,
                defaults=update_defaults
            )
            sent_ids.append(obj.id)
            
        ContactIcon.objects.filter(contact_info=contact_info).exclude(id__in=sent_ids).delete()

    def _update_contact_info_item(self, contact: ContactContent, info_data: dict) -> int:
        info_id = info_data.get("id")
        contact_info, _ = ContactInfo.objects.update_or_create(
            id=info_id if info_id else None,
            defaults={
                "contact": contact,
                "label": info_data.get("label"),
                "value": info_data.get("value"),
                "type": info_data.get("type"),
            }
        )
        
        icons_data = info_data.get("icon", [])
        self._update_contact_icons(contact_info, icons_data)
        
        return contact_info.id

    @transaction.atomic
    def update_contact_content(self, data: dict) -> ContactContent:
        contact_content = self.get_contact_content()
        if not contact_content:
            return None

        contact_content.title = data.get('title', contact_content.title)
        contact_content.description = data.get('description', contact_content.description)
        contact_content.save()

        if 'contact_infos' in data:
            info_sent_ids = []
            for info_data in data.get('contact_infos', []):
                info_id = self._update_contact_info_item(contact_content, info_data)
                info_sent_ids.append(info_id)
            
            ContactInfo.objects.filter(contact=contact_content).exclude(id__in=info_sent_ids).delete()
        if 'social_links' in data:
            self._update_social_links(contact_content, data.get('social_links', []))

        return contact_content


    def delete_contact_content(self) -> bool:
        contact_content = self.get_contact_content()
        if contact_content:
            contact_content.delete()
            return True
        return False

    def get_contact_content_translation(self, contact_content: ContactContent, language: str) -> Optional[ContactContentTranslation]:
        try:
            return contact_content.translations.get(language_code=language)
        except ContactContentTranslation.DoesNotExist:
            return None

    def upsert_contact_content_translation(self, contact_content: ContactContent, language: str, title: str, description: str) -> ContactContentTranslation:
        return ContactContentTranslation.objects.update_or_create(
            contact_content=contact_content,
            language_code=language,
            defaults={
                "title": title,
                "description": description,
            },
        )