from contextlib import asynccontextmanager

import anyio.to_thread
from dependency_injector import providers
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.session_route import router as sessions_router
from app.api.tutor_route import router as tutor_router
from app.api.user_route import router as users_router
from app.config import CORS_ORIGINS, THREAD_LIMIT
from app.containers import Container
from app.graph.graph import open_graph
from app.services.tutor_service import (
    LessonAlreadyStartedError,
    NoPendingQuizError,
    SessionBusyError,
    SessionNotFoundError,
)

# Domain and database errors mapped to an HTTP status and message.
_ERROR_RESPONSES: dict[type[Exception], tuple[int, str]] = {
    SessionNotFoundError: (status.HTTP_404_NOT_FOUND, "Session not found"),
    LessonAlreadyStartedError: (
        status.HTTP_409_CONFLICT,
        "Lesson already started for this session",
    ),
    NoPendingQuizError: (
        status.HTTP_409_CONFLICT,
        "No quiz awaiting an answer for this session",
    ),
    SessionBusyError: (
        status.HTTP_409_CONFLICT,
        "Another request for this session is still running",
    ),
    IntegrityError: (
        status.HTTP_409_CONFLICT,
        "Request conflicts with existing data or references a missing record",
    ),
}


def _error_handler(status_code: int, detail: str):
    async def handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return handler


def create_app() -> FastAPI:
    container = Container()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Blocking DB steps run in the thread pool.
        anyio.to_thread.current_default_thread_limiter().total_tokens = THREAD_LIMIT
        async with open_graph() as graph:
            container.graph.override(providers.Object(graph))
            try:
                yield
            finally:
                container.graph.reset_override()

    app = FastAPI(title="Agent Orchestrator", lifespan=lifespan)
    app.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    for exc_type, (status_code, detail) in _ERROR_RESPONSES.items():
        app.add_exception_handler(exc_type, _error_handler(status_code, detail))

    app.include_router(users_router)
    app.include_router(sessions_router)
    app.include_router(tutor_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
