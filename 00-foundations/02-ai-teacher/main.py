from __future__ import annotations

import logging
from typing import TypedDict

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()

MODEL_NAME = "gpt-4o-mini"

class InputState(BaseModel):
    """User-provided learning context."""

    level: str = Field(description="Current proficiency level of the user (e.g. 'A1', 'beginner').")
    language: str = Field(description="The language the user wants to learn.")
    lesson: str = Field(
        description="The lesson topic to generate, including key vocabulary, examples, and exercises."
    )


class FeedbackState(BaseModel):
    """Structured evaluation of the user's quiz answers."""

    score: int = Field(description="Score based on the number of questions in the quiz.")
    correct: int = Field(
        description="Number of correct answers. Must stay in sync with score and incorrect count."
    )
    incorrect: int = Field(
        description="Number of incorrect answers. Must stay in sync with score and correct count."
    )
    feedback: str = Field(
        description="Constructive feedback on the user's answers with concrete suggestions to improve."
    )


class LLMState(TypedDict):
    input: InputState
    feedback: FeedbackState
    lesson: str
    quiz: str
    answer: str


def build_model() -> ChatOpenAI:
    """Create the chat model.

    Note: ``verify=False`` disables TLS verification and is intended only for
    local development behind an intercepting proxy. Do not use in production.
    """
    return ChatOpenAI(
        model=MODEL_NAME,
        http_client=httpx.Client(verify=False),
    )


model = build_model()
evaluation_model = model.with_structured_output(FeedbackState)


def lesson_prompt(user_input: dict) -> str:
    return f"""
    You are an AI {user_input["language"]} language expert.
    The user is currently at the {user_input["level"]} level.
    Lesson topic: {user_input["lesson"]}

    Generate a lesson for the user at their current level with important word
    translations and examples. For example:

    Lesson: Greetings in Spanish (A1)

    Vocabulary:
    - Hola        -> Hello
    - Buenos dias -> Good morning
    - Como estas? -> How are you?

    Grammar Tip:
    Spanish has formal (usted) and informal (tu) forms.
    Use "usted" with strangers or elders.

    Example Dialogue:
    A: Hola! Como estas?
    B: Bien, gracias! Y tu?
    """


def quiz_prompt(state: LLMState) -> str:
    return f"""
    You are an AI quiz generator.
    Current profile of user: {state["input"]}
    Based on this lesson: {state["lesson"]}

    Generate exactly two quiz questions, scoped to the lesson:
    1. A translation question.
    2. A complete-the-sentence question.
    """


def evaluation_prompt(state: LLMState) -> str:
    return f"""
    You are a language expert. Evaluate the user's answers based on the
    provided lesson and quiz.

    Lesson: {state["lesson"]}
    Quiz: {state["quiz"]}
    User answer: {state["answer"]}
    """


def generate_lesson(state: LLMState) -> LLMState:
    response = model.invoke(lesson_prompt(state["input"]))

    state["lesson"] = response.content

    console.rule("[bold cyan]Lesson")
    console.print(Markdown(response.content))

    return state


def generate_quiz(state: LLMState) -> LLMState:
    response = model.invoke(quiz_prompt(state))

    state["quiz"] = response.content

    console.rule("[bold cyan]Quiz")
    console.print(Markdown(response.content))

    answer = input("Enter your answer here: ")
    state["answer"] = answer

    console.rule("[bold cyan]Answer")
    console.print(Markdown(answer))

    return state


def evaluation_and_feedback(state: LLMState) -> LLMState:
    response = evaluation_model.invoke(evaluation_prompt(state))

    state["feedback"] = response

    feedback_md = f"""
    **Score:** {response.score}

    **Correct:** {response.correct}  
    **Incorrect:** {response.incorrect}

    {response.feedback}
    """

    console.rule("[bold cyan]Feedback")
    console.print(Markdown(feedback_md))

    return state


def build_workflow():
    """Assemble and compile the LangGraph workflow."""
    graph = StateGraph(LLMState)

    graph.add_node("generate_lesson", generate_lesson)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("evaluation_and_feedback", evaluation_and_feedback)

    graph.add_edge(START, "generate_lesson")
    graph.add_edge("generate_lesson", "generate_quiz")
    graph.add_edge("generate_quiz", "evaluation_and_feedback")
    graph.add_edge("evaluation_and_feedback", END)

    return graph.compile()


def main() -> None:
    level = input("Enter your level: ")
    language = input("Enter language: ")
    lesson = input("Enter your lesson: ")

    initial_state: LLMState = {
        "input": {
            "level": level,
            "language": language,
            "lesson": lesson,
        },
        "feedback": {},
        "lesson": "",
        "quiz": "",
        "answer": "",
    }

    workflow = build_workflow()
    workflow.invoke(initial_state)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception:
        logger.exception("Workflow failed")
