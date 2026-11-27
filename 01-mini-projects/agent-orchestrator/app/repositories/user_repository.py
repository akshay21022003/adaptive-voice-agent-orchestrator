from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.repositories.user_repository_interface import IUserRepository


class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str | None = None) -> User:
        user = User(name=name)

        self.db.add(user)
        self.db.flush()

        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_all(self) -> list[User]:
        return list(self.db.scalars(select(User)).all())

    def delete(self, user_id: UUID) -> bool:
        user = self.db.get(User, user_id)
        if user is None:
            return False

        self.db.delete(user)
        self.db.flush()
        return True
