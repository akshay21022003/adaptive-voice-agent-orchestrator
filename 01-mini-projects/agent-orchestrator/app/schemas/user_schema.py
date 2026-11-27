from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Request body for creating a user. ``id`` is server-generated."""

    name: str | None = None


class UserRead(BaseModel):
    """Response model exposed to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None
