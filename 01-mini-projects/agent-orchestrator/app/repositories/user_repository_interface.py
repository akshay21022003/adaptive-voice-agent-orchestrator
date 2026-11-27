from abc import ABC, abstractmethod
from uuid import UUID

from app.db.models.user import User


class IUserRepository(ABC):

    @abstractmethod
    def create(self, name: str | None = None) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: UUID) -> bool:
        raise NotImplementedError
