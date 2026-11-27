from functools import lru_cache

import httpx
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from app.config import (
    OPENAI_API_KEY,
    OPENAI_MAX_RETRIES,
    OPENAI_MODEL,
    OPENAI_SSL_VERIFY,
    OPENAI_TIMEOUT_SECONDS,
)
from app.graph.prompts import evaluation_prompt, lesson_prompt, quiz_prompt
from app.graph.state import Feedback, TutorState


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        timeout=OPENAI_TIMEOUT_SECONDS,
        max_retries=OPENAI_MAX_RETRIES,
        http_async_client=httpx.AsyncClient(verify=OPENAI_SSL_VERIFY),
    )


async def generate_lesson(state: TutorState) -> dict:
    response = await get_model().ainvoke(lesson_prompt(state))
    return {"lesson": response.content}


async def generate_quiz(state: TutorState) -> dict:
    response = await get_model().ainvoke(quiz_prompt(state))
    return {"quiz": response.content}


def collect_answer(state: TutorState) -> dict:
    """Pause the graph until the caller resumes it with the user's answer."""
    answer = interrupt({"quiz": state["quiz"]})
    return {"answer": answer}


async def evaluate(state: TutorState) -> dict:
    result = (
        await get_model()
        .with_structured_output(Feedback)
        .ainvoke(evaluation_prompt(state))
    )
    return {"feedback": result.model_dump()}
