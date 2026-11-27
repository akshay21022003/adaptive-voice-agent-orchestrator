import asyncio


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Event loop factory for uvicorn (``--loop app.loop:selector_loop_factory``).

    psycopg's async mode, used by the LangGraph Postgres checkpointer, cannot
    run on Windows' default ProactorEventLoop.
    """
    return asyncio.SelectorEventLoop()
