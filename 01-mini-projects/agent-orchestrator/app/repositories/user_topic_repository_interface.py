from abc import ABC, abstractmethod
from uuid import UUID

from app.db.models.user_topic import UserTopic


class IUserTopicRepository(ABC):
    @abstractmethod
    def create(
        self, user_id: UUID, topic: str, score: float | None, feedback: dict
    ) -> UserTopic:
        raise NotImplementedError

    @abstractmethod
    def get_all_by_user_id(self, user_id: UUID) -> list[UserTopic]:
        raise NotImplementedError
