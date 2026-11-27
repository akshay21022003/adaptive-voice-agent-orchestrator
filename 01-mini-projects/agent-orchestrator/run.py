"""Start the API: ``python run.py`` (from this directory).

Equivalent to ``uvicorn app.main:app --loop app.loop:selector_loop_factory``.
Extra options (``--reload``, ``--workers 4``, ``--port 8001``) can be added to
the uvicorn command the same way.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        loop="app.loop:selector_loop_factory",
        reload=True,
    )
