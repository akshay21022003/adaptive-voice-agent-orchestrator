from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.session import Session
from app.db.models.timestamp_mixin import TimestampMixin


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    # Caller may supply a GUID; if none is provided, uuid4 generates one on insert.
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    session_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(Session.id), index=True
    )

    role: Mapped[str] = mapped_column(String(20))

    content: Mapped[str] = mapped_column(Text)
