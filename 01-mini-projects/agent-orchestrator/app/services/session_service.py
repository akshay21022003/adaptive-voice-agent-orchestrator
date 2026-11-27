from uuid import UUID

from app.db.models.session import Session
from app.repositories.session_repository_interface import ISessionRepository
from app.utils.enums import SessionStatus


class SessionService:
    def __init__(
        self,
        session_repository: ISessionRepository,
    ):
        self.session_repository = session_repository

    def create_session(
        self,
        session_id: UUID,
        user_id: UUID,
        topic: str,
    ) -> Session:
        session = Session(
            id=session_id,
            user_id=user_id,
            topic=topic,
            status=SessionStatus.IN_PROGRESS,
        )
        return self.session_repository.create(session=session)

    def get_session(self, session_id: UUID) -> Session | None:
        return self.session_repository.get_by_id(session_id)

    def list_sessions_for_user(self, user_id: UUID) -> list[Session]:
        """Return the user's sessions, newest first."""
        return self.session_repository.get_all_by_user_id(user_id)

    def update_session(
        self,
        session_id: UUID,
        user_id: UUID,
        topic: str,
        status: SessionStatus,
    ) -> Session | None:
        """Update an existing session. Returns ``None`` if it does not exist."""
        session = self.session_repository.get_by_id(session_id)
        if session is None:
            return None
        session.user_id = user_id
        session.topic = topic
        session.status = status
        return self.session_repository.update(session=session)

    def delete_session(self, session_id: UUID) -> bool:
        return self.session_repository.delete(session_id=session_id)
