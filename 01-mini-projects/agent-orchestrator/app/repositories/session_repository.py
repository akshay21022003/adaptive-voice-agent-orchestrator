from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.models.session import Session
from app.repositories.session_repository_interface import ISessionRepository


class SessionRepository(ISessionRepository):
    def __init__(self, db: DbSession):
        self.db = db

    def get_by_id(self, session_id: UUID) -> Session | None:
        return self.db.get(Session, session_id)

    def get_all(self) -> list[Session]:
        return list(self.db.scalars(select(Session)).all())

    def get_all_by_user_id(self, user_id: UUID) -> list[Session]:
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.desc(), Session.id)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, session: Session) -> Session:
        self.db.add(session)
        self.db.flush()
        return session

    def update(self, session: Session) -> Session:
        merged = self.db.merge(session)
        self.db.flush()
        return merged

    def delete(self, session_id: UUID) -> bool:
        session = self.db.get(Session, session_id)
        if session is None:
            return False

        self.db.delete(session)
        self.db.flush()
        return True
