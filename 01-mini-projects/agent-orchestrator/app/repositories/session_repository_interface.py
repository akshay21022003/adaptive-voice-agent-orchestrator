from abc import ABC, abstractmethod
from uuid import UUID

from app.db.models.session import Session


class ISessionRepository(ABC):

    @abstractmethod
    def get_by_id(self, session_id: UUID) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[Session]:
        raise NotImplementedError

    @abstractmethod
    def get_all_by_user_id(self, user_id: UUID) -> list[Session]:
        raise NotImplementedError

    @abstractmethod
    def create(self, session) -> Session:
        raise NotImplementedError

    @abstractmethod
    def update(self, session) -> Session:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id) -> bool:
        raise NotImplementedError
