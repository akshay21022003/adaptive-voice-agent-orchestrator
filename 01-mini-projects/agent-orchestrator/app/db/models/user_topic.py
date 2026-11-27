from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.timestamp_mixin import TimestampMixin
from app.db.models.user import User


class UserTopic(TimestampMixin, Base):
    __tablename__ = "user_topics"

    # Caller may supply a GUID; if none is provided, uuid4 generates one on insert.
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(User.id), index=True
    )

    topic: Mapped[str] = mapped_column(String(255), index=True)

    score: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)

    feedback: Mapped[str] = mapped_column(JSON)
