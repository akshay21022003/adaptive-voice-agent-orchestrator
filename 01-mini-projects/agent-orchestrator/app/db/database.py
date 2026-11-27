from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_SIZE

engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Request-scoped DB session.

    Repositories only ``add``/``flush`` (staging work and getting IDs). This
    dependency owns the single commit per request: if the handler returns
    successfully the transaction is committed, otherwise it is rolled back.
    The session is always closed at the end.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
