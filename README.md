The project uses **PostgreSQL** running in Docker, with **pgAdmin** as a web UI for browsing the database. Schema changes are managed with **Alembic**.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python environment with dependencies from `requirements.txt` installed (for running migrations)

### Configuration

Database and pgAdmin credentials live in `.env` at the project root. Compose falls back to sensible defaults if they are missing:

| Variable            | Default                                                            | Purpose                                    |
| ------------------- | ----------------------------------------------------------------- | ------------------------------------------ |
| `POSTGRES_USER`     | `postgres`                                                        | Postgres username                          |
| `POSTGRES_PASSWORD` | `password`                                                        | Postgres password                          |
| `POSTGRES_DB`       | `mini-agent`                                                      | Database created on first container start  |
| `DATABASE_URL`      | `postgresql+psycopg2://postgres:password@localhost:5432/mini-agent` | SQLAlchemy / Alembic connection string     |
| `PGADMIN_EMAIL`     | `admin@admin.com`                                                | pgAdmin login email                        |
| `PGADMIN_PASSWORD`  | `admin`                                                          | pgAdmin login password                     |

> **Driver note:** the URL uses `postgresql+psycopg2` explicitly. SQLAlchemy 2.x otherwise defaults to the `psycopg` (v3) driver, which is not installed — the project uses `psycopg2-binary`.

> `.env` also holds secrets like `OPENAI_API_KEY`. Keep it out of version control (see `.gitignore`).

### First-time setup on a new machine

The pgAdmin bind-mount files (`pgadmin/pgpass` and `pgadmin/servers.json`) are **committed** with local dev defaults, so they're already present after a clone — no setup needed for pgAdmin.

The only file you must create is `.env`, since it holds your real `OPENAI_API_KEY`:

**PowerShell (Windows):**

```powershell
Copy-Item .env.example .env   # then edit .env and add your OPENAI_API_KEY
```

**bash (macOS / Linux):**

```bash
cp .env.example .env   # then edit .env and add your OPENAI_API_KEY
```

> `pgadmin/pgpass` and `pgadmin/servers.json` carry the non-secret local `password`. If you change `POSTGRES_USER` / `POSTGRES_PASSWORD`, update `pgadmin/pgpass` (`host:port:db:user:password`) and the `Username` in `pgadmin/servers.json` to match. Don't commit a *real* password here — git-ignore these files at that point instead.

### Start the stack

Run from the project root:

```bash
docker compose up -d
```

This starts two containers:

| Service    | Container       | URL / Port              |
| ---------- | --------------- | ----------------------- |
| PostgreSQL | `avao_postgres` | `localhost:5432`        |
| pgAdmin    | `avao_pgadmin`  | http://localhost:5050   |

Data is stored in named volumes (`postgres_data`, `pgadmin_data`), so it persists across restarts.

> The `mini-agent` database is auto-created only on the **first** startup with an empty `postgres_data` volume (from `POSTGRES_DB`). If you connect to a database name that doesn't exist yet, create it manually:
>
> ```bash
> echo 'CREATE DATABASE "mini-agent";' | docker exec -i avao_postgres psql -U postgres
> ```
>
> The quotes are required because the name contains a hyphen.

### Configuration in code

`app/config.py` loads `.env` and exposes a single source of truth:

- `DATABASE_URL` — read by both `app/db/database.py` (SQLAlchemy engine) and `alembic/env.py` (migrations).
- `OPENAI_API_KEY`

No code change is needed if you keep the default credentials.

### Migrations (Alembic)

#### One-time setup (already done — reference only)

Alembic is **already initialized** in this repo (`alembic.ini` + the `alembic/` folder are committed), so on a normal clone you **skip this section** and go straight to the workflow below. This is documented only in case someone needs to recreate it from scratch (e.g. the `alembic/` folder was deleted).

1. **Install deps** (already in `requirements.txt`): `alembic`, `sqlalchemy`, `psycopg2-binary`.
2. **Initialize the scaffold** from `01-mini-projects/agent-orchestrator`:
   ```powershell
   alembic init alembic
   ```
   This generates `alembic.ini` (which holds the `script_location` key) plus `alembic/env.py`, `alembic/versions/`, and `alembic/script.py.mako`.
3. **Point Alembic at the app's models and DB URL** by editing `alembic/env.py`. The key edits (near the top, before `target_metadata`):
   ```python
   import os, sys

   # make the `app` package importable no matter where alembic is run from
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

   from app.config import DATABASE_URL
   from app.db.database import Base
   import app.db.models  # noqa: F401  — registers every model on Base.metadata

   config = context.config
   config.set_main_option("sqlalchemy.url", DATABASE_URL)  # URL from .env, not the ini
   ...
   target_metadata = Base.metadata  # was None
   ```
4. **Neutralize the placeholder URL** in `alembic.ini` so it isn't mistaken for the real one (the runtime override in `env.py` wins regardless):
   ```ini
   # sqlalchemy.url =    # set at runtime in env.py from app.config.DATABASE_URL
   ```
5. **Ensure every model is imported** in `app/db/models/__init__.py` (autogenerate only sees models that are imported). Confirm with:
   ```powershell
   python -c "import app.db.models; from app.db.database import Base; print(sorted(Base.metadata.tables))"
   ```
6. **Generate and apply** the first migration (see workflow below).

#### Day-to-day usage

> **Run from `01-mini-projects/agent-orchestrator`** — *not* from the repo root or `01-mini-projects`.
> Alembic (and the `app` package import) only resolve from this directory. Running elsewhere gives
> `No 'script_location' key found in configuration` (the `alembic.ini` isn't found) or `ModuleNotFoundError: app`.

```powershell
# from 01-mini-projects/agent-orchestrator
alembic revision --autogenerate -m "your message"   # generate a migration from model changes
alembic upgrade head                                 # apply all pending migrations
alembic downgrade -1                                 # roll back one migration
alembic current                                      # show the currently applied revision
alembic history                                      # list all revisions
```

**Typical workflow after changing a model:**

1. Edit or add a model under `app/db/models/`.
2. Make sure it's imported in `app/db/models/__init__.py` (see below).
3. `alembic revision --autogenerate -m "describe the change"`
4. Open the generated file in `alembic/versions/` and sanity-check it.
5. `alembic upgrade head` to apply it.

#### How it's wired (so autogenerate actually sees your models)

- **One `Base`.** All models inherit from the single `Base` in `app/db/database.py`. Don't define a second `DeclarativeBase` anywhere — duplicate `Base` classes give each its own `metadata`, and autogenerate will miss half your tables.
- **All models must be imported before autogenerate runs.** `app/db/models/__init__.py` imports every model (`User`, `Session`, `Message`, `UserTopic`). `alembic/env.py` does `import app.db.models`, which registers them all on `Base.metadata`. **When you add a new model, add it to `app/db/models/__init__.py`** or autogenerate won't detect its table.
- **The DB URL comes from `.env`, not `alembic.ini`.** `alembic/env.py` sets `sqlalchemy.url` at runtime from `DATABASE_URL` in `app/config.py`, so the placeholder in `alembic.ini` stays commented out. Migrations always target the same database as the app.

#### Troubleshooting

| Symptom | Cause / fix |
| ------- | ----------- |
| `No 'script_location' key found in configuration` | You're in the wrong directory. `cd` into `01-mini-projects/agent-orchestrator`. |
| `ModuleNotFoundError: No module named 'app'` | Same — run from `01-mini-projects/agent-orchestrator`. |
| Autogenerate produces an empty migration | Your new model isn't imported in `app/db/models/__init__.py`. |
| `NameError` / missing `String`, `Numeric`, etc. when importing models | The model file is missing a SQLAlchemy import. Verify quickly with: `python -c "import app.db.models; from app.db.database import Base; print(sorted(Base.metadata.tables))"` |
| Autogenerate can't connect to the DB | The Postgres container isn't running. `docker compose up -d` from the repo root first. |

### Use the pgAdmin UI

The `mini-agent` server is **pre-registered** on first startup via `pgadmin/servers.json` (credentials come from `pgadmin/pgpass`), so you don't need to add it manually.

1. Open http://localhost:5050. With server mode disabled it goes straight to the dashboard.
2. In the left tree, expand:

   ```
   Servers → mini-agent → Databases → mini-agent → Schemas → public → Tables
   ```

3. If prompted, the Postgres password is `password`.
4. Right-click a table → **View/Edit Data → All Rows** to see its contents.

> **Tables not showing?** pgAdmin caches the tree. Right-click the `mini-agent` **database** node → **Refresh**. Tables live under `Schemas → public → Tables`, not directly under the database.

> **Registering manually** (if the auto-import didn't run): right-click **Servers → Register → Server**, then on the **Connection** tab use Host `postgres` (the compose service name — *not* `localhost`, since pgAdmin reaches Postgres over the internal Docker network), Port `5432`, Maintenance DB `mini-agent`, Username `postgres`, Password `password`.

#### How `servers.json` works (and what deleting it does)

`pgadmin/servers.json` is only read **once, at pgAdmin startup**, to seed the connection. After the first boot, the registered server lives in the `pgadmin_data` volume (`/var/lib/pgadmin`) and persists independently of the file.

- **On an existing instance** (the `pgadmin_data` volume already holds the entry): deleting `servers.json` changes nothing you can see — the `mini-agent` server is already saved in the volume.
- **On a fresh start** (after `docker compose down -v` wipes `pgadmin_data`): without the file, the server is *not* auto-created and you'd register it manually (see above).

> **Fixing the "not a directory" mount error:** if pgAdmin won't start and Docker complains about mounting a directory onto a file, it means `pgadmin/pgpass` and/or `pgadmin/servers.json` got auto-created as empty directories (they were missing when compose ran). Since these files are committed, this normally only happens if they were deleted. Restore them from git and restart:
>
> ```powershell
> docker compose down
> Remove-Item -Recurse -Force pgadmin/pgpass, pgadmin/servers.json
> git checkout -- pgadmin/pgpass pgadmin/servers.json
> docker compose up -d
> ```

> **Caveat if you delete the file but keep the mount:** the compose volume line `./pgadmin/servers.json:/pgadmin4/servers.json:ro` expects the source to exist. If it's missing, Docker creates a *directory* at that path and pgAdmin logs an error trying to read it as JSON — harmless, but noisy. To remove the auto-registration cleanly, also delete these two lines from `docker-compose.yml`:
>
> ```yaml
> PGADMIN_SERVER_JSON_FILE: /pgadmin4/servers.json          # env line
> - ./pgadmin/servers.json:/pgadmin4/servers.json:ro        # volume mount
> ```

### Common commands

Run all of these from the project root:

```bash
docker compose ps            # show container status
docker compose stop          # stop containers (keep data)
docker compose up -d         # start again
docker compose down          # remove containers (keep data)
docker compose down -v       # remove containers AND wipe data (fresh DB next start)
docker compose logs -f       # follow logs
```

> After `docker compose down -v`, the `postgres_data` volume is wiped, so `mini-agent` is auto-created again on the next start, and you'll need to re-run `alembic upgrade head` to recreate the tables.

### Running the agent orchestrator API

From `01-mini-projects/agent-orchestrator` (with Postgres running and `alembic upgrade head` applied):

```powershell
python run.py
```

Docs at http://localhost:8000/docs. 
un.py starts uvicorn with a selector event loop (--loop app.loop:selector_loop_factory). This is required on Windows because psycopg's async mode, used by the checkpointer, does not work on the default ProactorEventLoop. If you launch uvicorn yourself, pass that same flag; otherwise startup fails with an explanatory error. The LangGraph checkpoint tables are created automatically on startup.

Tutor flow (the session id is also the LangGraph thread id):

1. `POST /users` then `POST /sessions` (`id`, `user_id`, `topic`) to create a user and session.
2. `POST /tutor/start` with `session_id`, `level`, `language`, `lesson`. Returns the generated lesson and quiz, and the graph pauses.
3. `POST /tutor/answer` with `session_id`, `answer`. Resumes the graph and returns score and feedback. The result is saved to `user_topics` and the session becomes `completed`.
4. `GET /tutor/{session_id}/messages` returns the conversation history.

#### Scaling notes

- Tutor requests open short DB transactions only around reads and writes, so no DB connection is held during LLM calls. Concurrency is limited by `THREAD_LIMIT` (default 100) and by your OpenAI rate limits.
- To use more CPU cores, run several workers: `uvicorn app.main:app --loop app.loop:selector_loop_factory --workers 4`. Each worker opens its own pools, so keep `(DB_POOL_SIZE + DB_MAX_OVERFLOW + CHECKPOINT_POOL_SIZE) * workers` below Postgres' `max_connections` (default 100).
- A second request for a session that is still running gets `409`. This guard is per process, so with several workers it does not stop two workers from running the same session at once.
- If the LLM call or the DB write fails partway, repeating the same `/tutor/start` or `/tutor/answer` request resumes from the saved checkpoint.

#### CORS and read endpoints

- Browsers may only call the API from the origins in `CORS_ORIGINS` (comma separated, default `http://localhost:5173`, the Vite dev server). Set it in `.env` and add the frontend's URL when you deploy. Wildcards are not used.
- `GET /sessions/{session_id}` returns one session, and `GET /users/{user_id}/sessions` returns a user's sessions, newest first. Both return `404` for an unknown id.
