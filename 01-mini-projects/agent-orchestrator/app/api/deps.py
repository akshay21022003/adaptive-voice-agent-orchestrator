from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.db.database import get_db
from app.services.session_service import SessionService
from app.services.tutor_service import TutorService
from app.services.user_service import UserService


def get_user_service(request: Request, db: DbSession = Depends(get_db)) -> UserService:
    return request.app.container.user_service(user_repository__db=db)


def get_session_service(
    request: Request, db: DbSession = Depends(get_db)
) -> SessionService:
    return request.app.container.session_service(session_repository__db=db)


def get_tutor_service(request: Request) -> TutorService:
    return request.app.container.tutor_service()
