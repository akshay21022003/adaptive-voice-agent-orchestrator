from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models.message import Message
from app.repositories.message_repository_interface import IMessageRepository


class MessageRepository(IMessageRepository):
    def __init__(self, db: DbSession):
        self.db = db

    def create(self, session_id: UUID, role: str, content: str) -> Message:
        message = Message(session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.flush()
        return message

    def get_all_by_session_id(self, session_id: UUID) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(self.db.scalars(stmt).all())
