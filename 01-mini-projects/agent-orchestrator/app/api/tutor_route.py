from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_tutor_service
from app.schemas.tutor_schema import (
    MessageRead,
    TutorAnswer,
    TutorFeedbackRead,
    TutorStart,
    TutorStartRead,
)
from app.services.tutor_service import TutorService

# Domain errors (session not found, already started, busy, ...) are mapped to
# HTTP responses by the exception handlers registered in ``app.main``.
router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/start", response_model=TutorStartRead)
async def start_lesson(
    payload: TutorStart,
    service: TutorService = Depends(get_tutor_service),
) -> TutorStartRead:
    result = await service.start(
        session_id=payload.session_id,
        level=payload.level,
        language=payload.language,
        lesson=payload.lesson,
    )
    return TutorStartRead(session_id=payload.session_id, **result)


@router.post("/answer", response_model=TutorFeedbackRead)
async def submit_answer(
    payload: TutorAnswer,
    service: TutorService = Depends(get_tutor_service),
) -> TutorFeedbackRead:
    feedback = await service.answer(payload.session_id, payload.answer)
    return TutorFeedbackRead(session_id=payload.session_id, **feedback)


@router.get("/{session_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session_id: UUID,
    service: TutorService = Depends(get_tutor_service),
) -> list[MessageRead]:
    messages = await service.list_messages(session_id)
    return [MessageRead.model_validate(m) for m in messages]
