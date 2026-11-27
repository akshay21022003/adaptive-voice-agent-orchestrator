import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import CHECKPOINT_DATABASE_URL, CHECKPOINT_POOL_SIZE
from app.graph.nodes import collect_answer, evaluate, generate_lesson, generate_quiz
from app.graph.state import TutorState

# Node the graph pauses at while waiting for the user's answer.
COLLECT_ANSWER = "collect_answer"


def build_graph(checkpointer: BaseCheckpointSaver):
    """Lesson -> quiz -> (pause for answer) -> evaluation."""
    graph = StateGraph(TutorState)

    graph.add_node("generate_lesson", generate_lesson)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node(COLLECT_ANSWER, collect_answer)
    graph.add_node("evaluate", evaluate)

    graph.add_edge(START, "generate_lesson")
    graph.add_edge("generate_lesson", "generate_quiz")
    graph.add_edge("generate_quiz", COLLECT_ANSWER)
    graph.add_edge(COLLECT_ANSWER, "evaluate")
    graph.add_edge("evaluate", END)

    return graph.compile(checkpointer=checkpointer)


@asynccontextmanager
async def open_graph() -> AsyncIterator:
    """Open the async checkpointer pool and yield the compiled graph.

    The pool lives for the whole app lifetime and is closed on exit.
    Checkpoint tables are created on first use.
    """
    if sys.platform == "win32" and isinstance(
        asyncio.get_running_loop(), asyncio.ProactorEventLoop
    ):
        raise RuntimeError(
            "psycopg async cannot run on Windows' ProactorEventLoop. Start the app "
            "with `python run.py` or `uvicorn app.main:app "
            "--loop app.loop:selector_loop_factory`."
        )
    async with AsyncConnectionPool(
        CHECKPOINT_DATABASE_URL,
        max_size=CHECKPOINT_POOL_SIZE,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        yield build_graph(checkpointer)
