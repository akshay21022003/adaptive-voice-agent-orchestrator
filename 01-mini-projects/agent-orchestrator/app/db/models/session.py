from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.timestamp_mixin import TimestampMixin
from app.db.models.user import User


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(User.id), index=True
    )

    topic: Mapped[str] = mapped_column(String(255), index=True)

    status: Mapped[str] = mapped_column(String(50), index=True)
