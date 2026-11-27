import os
from pathlib import Path

from dotenv import load_dotenv

# Load the project-root .env (four levels up: app -> agent-orchestrator ->
# 01-mini-projects -> repo root).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:password@localhost:5432/mini-agent",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LangGraph's Postgres checkpointer uses psycopg (v3), which does not accept
# the SQLAlchemy "+psycopg2" driver suffix.
CHECKPOINT_DATABASE_URL = DATABASE_URL.replace("+psycopg2", "")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Set OPENAI_SSL_VERIFY=false only for local dev behind an intercepting proxy.
OPENAI_SSL_VERIFY = os.getenv("OPENAI_SSL_VERIFY", "true").lower() != "false"

OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
# The OpenAI client retries 429/5xx responses with exponential backoff.
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "4"))

# Per-process connection limits. Keep (DB_POOL_SIZE + DB_MAX_OVERFLOW +
# CHECKPOINT_POOL_SIZE) * workers below Postgres' max_connections (default 100).
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
CHECKPOINT_POOL_SIZE = int(os.getenv("CHECKPOINT_POOL_SIZE", "10"))

# Worker threads for the blocking DB steps (the async routes run them in a pool).
THREAD_LIMIT = int(os.getenv("THREAD_LIMIT", "100"))

# Browser origins allowed to call the API (comma separated). No wildcard.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
