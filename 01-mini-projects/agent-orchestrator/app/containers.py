from dependency_injector import containers, providers

from app.db.database import SessionLocal
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_topic_repository import UserTopicRepository
from app.services.session_service import SessionService
from app.services.tutor_service import TutorService
from app.services.user_service import UserService


class Container(containers.DeclarativeContainer):
    """Application dependency-injection container.

    Repositories need a per-request DB session, so they are declared without
    one. ``app.api.deps`` creates the session (``get_db``: commit on success,
    rollback on error, always close) and passes it in when resolving a
    service, e.g. ``container.user_service(user_repository__db=db)``.

    ``TutorService`` opens its own short transactions so no connection is
    held during LLM calls. ``graph`` is supplied at app startup by the
    lifespan in ``app.main`` (async checkpointer pool, closed on shutdown).
    """

    graph = providers.Dependency()

    user_repository = providers.Factory(UserRepository)
    session_repository = providers.Factory(SessionRepository)
    message_repository = providers.Factory(MessageRepository)
    user_topic_repository = providers.Factory(UserTopicRepository)

    user_service = providers.Factory(UserService, user_repository=user_repository)
    session_service = providers.Factory(
        SessionService, session_repository=session_repository
    )
    tutor_service = providers.Factory(
        TutorService,
        graph=graph,
        db_session_factory=providers.Object(SessionLocal),
        session_repository_factory=session_repository.provider,
        message_repository_factory=message_repository.provider,
        user_topic_repository_factory=user_topic_repository.provider,
    )
