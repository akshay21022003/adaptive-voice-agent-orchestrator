from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.timestamp_mixin import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # Caller may supply a GUID (e.g. generated on the frontend).
    # If none is provided, uuid4 generates one on insert.
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
