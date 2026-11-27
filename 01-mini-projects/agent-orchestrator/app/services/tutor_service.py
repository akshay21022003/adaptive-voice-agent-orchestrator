import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from langgraph.types import Command
from starlette.concurrency import run_in_threadpool

from app.graph.graph import COLLECT_ANSWER
from app.repositories.message_repository_interface import IMessageRepository
from app.repositories.session_repository_interface import ISessionRepository
from app.repositories.user_topic_repository_interface import IUserTopicRepository
from app.utils.enums import MessageRole, SessionStatus

logger = logging.getLogger(__name__)

# Sessions with a request in flight. Services are created per request, so the
# registry has to be module-level to be shared.
_in_flight: set[UUID] = set()
_in_flight_lock = threading.Lock()


class SessionNotFoundError(Exception):
    pass


class LessonAlreadyStartedError(Exception):
    pass


class NoPendingQuizError(Exception):
    pass


class SessionBusyError(Exception):
    """Another request for the same session is still running."""


@contextmanager
def _session_guard(session_id: UUID) -> Iterator[None]:
    """Reject a second concurrent request for the same session.

    The registry is per process. With several workers, two of them can still
    run the same session at once.
    """
    with _in_flight_lock:
        if session_id in _in_flight:
            raise SessionBusyError(str(session_id))
        _in_flight.add(session_id)
    try:
        yield
    finally:
        with _in_flight_lock:
            _in_flight.discard(session_id)


@dataclass(frozen=True)
class _Repositories:
    sessions: ISessionRepository
    messages: IMessageRepository
    user_topics: IUserTopicRepository


def _format_feedback(feedback: dict) -> str:
    return (
        f"Score: {feedback['score']} "
        f"(correct: {feedback['correct']}, incorrect: {feedback['incorrect']})"
        f"\n\n{feedback['feedback']}"
    )


class TutorService:
    """Runs the tutor graph and stores the conversation.

    The graph runs on the event loop. SQLAlchemy is blocking, so each DB step
    runs in the thread pool inside its own short transaction. No connection
    is held while waiting on the LLM.
    """

    def __init__(
        self,
        graph,
        db_session_factory: Callable,
        session_repository_factory: Callable[..., ISessionRepository],
        message_repository_factory: Callable[..., IMessageRepository],
        user_topic_repository_factory: Callable[..., IUserTopicRepository],
    ):
        self.graph = graph
        self._db_session_factory = db_session_factory
        self._session_repository_factory = session_repository_factory
        self._message_repository_factory = message_repository_factory
        self._user_topic_repository_factory = user_topic_repository_factory

    @contextmanager
    def _transaction(self) -> Iterator[_Repositories]:
        db = self._db_session_factory()
        try:
            yield _Repositories(
                sessions=self._session_repository_factory(db=db),
                messages=self._message_repository_factory(db=db),
                user_topics=self._user_topic_repository_factory(db=db),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _graph_config(session_id: UUID) -> dict:
        # The session id doubles as the LangGraph thread id.
        return {"configurable": {"thread_id": str(session_id)}}

    # Blocking DB steps. Called through run_in_threadpool.

    def _has_messages(self, session_id: UUID) -> bool:
        with self._transaction() as repos:
            if repos.sessions.get_by_id(session_id) is None:
                raise SessionNotFoundError(str(session_id))
            return bool(repos.messages.get_all_by_session_id(session_id))

    def _save_lesson(self, session_id: UUID, state: dict) -> None:
        with self._transaction() as repos:
            repos.messages.create(session_id, MessageRole.ASSISTANT, state["lesson"])
            repos.messages.create(session_id, MessageRole.ASSISTANT, state["quiz"])

    def _load_session_for_answer(self, session_id: UUID) -> tuple[UUID, str, bool]:
        """Return the session's ``(user_id, topic, is_completed)``."""
        with self._transaction() as repos:
            session = repos.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(str(session_id))
            return (
                session.user_id,
                session.topic,
                session.status == SessionStatus.COMPLETED,
            )

    def _save_result(
        self, session_id: UUID, user_id: UUID, topic: str, state: dict
    ) -> None:
        feedback = state["feedback"]
        with self._transaction() as repos:
            repos.messages.create(session_id, MessageRole.USER, state["answer"])
            repos.messages.create(
                session_id, MessageRole.ASSISTANT, _format_feedback(feedback)
            )
            repos.user_topics.create(
                user_id=user_id,
                topic=topic,
                score=feedback["score"],
                feedback=feedback,
            )
            session = repos.sessions.get_by_id(session_id)
            session.status = SessionStatus.COMPLETED

    def _list_messages(self, session_id: UUID) -> list[dict]:
        with self._transaction() as repos:
            if repos.sessions.get_by_id(session_id) is None:
                raise SessionNotFoundError(str(session_id))
            # Plain dicts, because ORM objects are detached once the
            # transaction closes.
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at,
                }
                for m in repos.messages.get_all_by_session_id(session_id)
            ]

    # Public API.

    async def start(
        self, session_id: UUID, level: str, language: str, lesson: str
    ) -> dict:
        """Generate the lesson and quiz, then pause until the user answers.

        Safe to repeat after a failure: an interrupted graph continues from its
        checkpoint, and messages are only written once.
        """
        with _session_guard(session_id):
            has_messages = await run_in_threadpool(self._has_messages, session_id)
            config = self._graph_config(session_id)
            snapshot = await self.graph.aget_state(config)

            if snapshot.values and has_messages:
                raise LessonAlreadyStartedError(str(session_id))

            if not snapshot.values:
                await self.graph.ainvoke(
                    {"level": level, "language": language, "lesson_topic": lesson},
                    config,
                )
            elif snapshot.next and COLLECT_ANSWER not in snapshot.next:
                logger.warning("Resuming interrupted lesson for session %s", session_id)
                await self.graph.ainvoke(None, config)

            state = (await self.graph.aget_state(config)).values
            if not has_messages:
                await run_in_threadpool(self._save_lesson, session_id, state)
            return {"lesson": state["lesson"], "quiz": state["quiz"]}

    async def answer(self, session_id: UUID, answer: str) -> dict:
        """Evaluate the user's answer and complete the session.

        Safe to repeat after a failure, in the same way as ``start``.
        """
        with _session_guard(session_id):
            user_id, topic, completed = await run_in_threadpool(
                self._load_session_for_answer, session_id
            )
            config = self._graph_config(session_id)
            snapshot = await self.graph.aget_state(config)

            if COLLECT_ANSWER in snapshot.next:
                state = await self.graph.ainvoke(Command(resume=answer), config)
            elif snapshot.next:
                logger.warning(
                    "Resuming interrupted evaluation for session %s", session_id
                )
                state = await self.graph.ainvoke(None, config)
            elif snapshot.values.get("feedback") and not completed:
                logger.warning("Saving unsaved result for session %s", session_id)
                state = snapshot.values
            else:
                raise NoPendingQuizError(str(session_id))

            await run_in_threadpool(
                self._save_result, session_id, user_id, topic, state
            )
            return state["feedback"]

    async def list_messages(self, session_id: UUID) -> list[dict]:
        return await run_in_threadpool(self._list_messages, session_id)
