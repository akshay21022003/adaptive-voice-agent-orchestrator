from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.utils.enums import SessionStatus


class SessionCreate(BaseModel):
    """Request body for creating a session."""

    id: UUID
    user_id: UUID
    topic: str


class SessionUpdate(BaseModel):
    """Request body for updating a session."""

    id: UUID
    user_id: UUID
    topic: str
    status: SessionStatus


class SessionRead(BaseModel):
    """Response model exposed to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic: str
    status: SessionStatus
