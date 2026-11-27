from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_session_service, get_user_service
from app.schemas.session_schema import SessionRead
from app.schemas.user_schema import UserCreate, UserRead
from app.services.session_service import SessionService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = service.create_user(payload.name)
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
def list_users(
    service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    return [UserRead.model_validate(u) for u in service.list_users()]


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)


@router.get("/{user_id}/sessions", response_model=list[SessionRead])
def list_user_sessions(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionRead]:
    if user_service.get_user(user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    sessions = session_service.list_sessions_for_user(user_id)
    return [SessionRead.model_validate(s) for s in sessions]


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> None:
    deleted = service.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
