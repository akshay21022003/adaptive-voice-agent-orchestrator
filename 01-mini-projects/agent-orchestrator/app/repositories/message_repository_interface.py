from abc import ABC, abstractmethod
from uuid import UUID

from app.db.models.message import Message


class IMessageRepository(ABC):
    @abstractmethod
    def create(self, session_id: UUID, role: str, content: str) -> Message:
        raise NotImplementedError

    @abstractmethod
    def get_all_by_session_id(self, session_id: UUID) -> list[Message]:
        raise NotImplementedError
