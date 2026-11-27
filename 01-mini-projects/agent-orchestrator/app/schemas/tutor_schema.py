from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TutorStart(BaseModel):
    """Request body to start a lesson for an existing session."""

    session_id: UUID
    level: str
    language: str
    lesson: str


class TutorStartRead(BaseModel):
    session_id: UUID
    lesson: str
    quiz: str


class TutorAnswer(BaseModel):
    session_id: UUID
    answer: str


class TutorFeedbackRead(BaseModel):
    session_id: UUID
    score: int
    correct: int
    incorrect: int
    feedback: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
