from typing import TypedDict

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    """Structured evaluation of the user's quiz answers."""

    score: int = Field(
        description="Score based on the number of questions in the quiz."
    )
    correct: int = Field(description="Number of correct answers.")
    incorrect: int = Field(description="Number of incorrect answers.")
    feedback: str = Field(
        description="Constructive feedback with concrete suggestions to improve."
    )


class TutorState(TypedDict, total=False):
    # Inputs
    level: str
    language: str
    lesson_topic: str
    # Produced by the graph
    lesson: str
    quiz: str
    answer: str
    feedback: dict
