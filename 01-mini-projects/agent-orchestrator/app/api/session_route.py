from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_session_service
from app.schemas.session_schema import SessionCreate, SessionRead, SessionUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    session = service.create_session(
        session_id=payload.id, user_id=payload.user_id, topic=payload.topic
    )
    return SessionRead.model_validate(session)


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return SessionRead.model_validate(session)


@router.put("", response_model=SessionRead)
def update_session(
    payload: SessionUpdate,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    session = service.update_session(
        session_id=payload.id,
        user_id=payload.user_id,
        topic=payload.topic,
        status=payload.status,
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return SessionRead.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> None:
    deleted = service.delete_session(session_id=session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
