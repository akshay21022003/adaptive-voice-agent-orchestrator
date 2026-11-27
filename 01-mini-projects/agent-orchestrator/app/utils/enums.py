from enum import StrEnum


class SessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FEEDBACK_PENDING = "feedback_pending"
    COMPLETED = "completed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
