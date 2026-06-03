from abc import ABC, abstractmethod
from apps.contact_us.models import ContactMessage
class IContactMessage(ABC):
    @abstractmethod
    def get_all_contact_messages(self):
        pass
    @abstractmethod
    def get_contact_message_by_id(self,id:int) -> ContactMessage:
        pass
    @abstractmethod
    def create_contact_message(self, data: dict) -> ContactMessage:
        pass
    @abstractmethod
    def delete_contact_message(self,pk):
        pass 
    