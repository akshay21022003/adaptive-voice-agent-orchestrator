from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models.user_topic import UserTopic
from app.repositories.user_topic_repository_interface import IUserTopicRepository


class UserTopicRepository(IUserTopicRepository):
    def __init__(self, db: DbSession):
        self.db = db

    def create(
        self, user_id: UUID, topic: str, score: float | None, feedback: dict
    ) -> UserTopic:
        user_topic = UserTopic(
            user_id=user_id, topic=topic, score=score, feedback=feedback
        )
        self.db.add(user_topic)
        self.db.flush()
        return user_topic

    def get_all_by_user_id(self, user_id: UUID) -> list[UserTopic]:
        stmt = select(UserTopic).where(UserTopic.user_id == user_id)
        return list(self.db.scalars(stmt).all())
