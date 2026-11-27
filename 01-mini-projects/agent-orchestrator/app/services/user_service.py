from uuid import UUID

from app.db.models.user import User
from app.repositories.user_repository_interface import IUserRepository


class UserService:

    def __init__(
        self,
        user_repository: IUserRepository,
    ):
        self.user_repository = user_repository

    def create_user(self, name: str | None = None) -> User:
        return self.user_repository.create(name)

    def get_user(self, user_id: UUID) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def list_users(self) -> list[User]:
        return self.user_repository.get_all()

    def delete_user(self, user_id: UUID) -> bool:
        return self.user_repository.delete(user_id)
