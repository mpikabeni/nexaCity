from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class DemoProgress(Base):
    __tablename__ = "demo_progress"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    current_step: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_steps: Mapped[int] = mapped_column(
        Integer,
        default=12,
        nullable=False,
    )

    current_section: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    demo_started: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    demo_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    skipped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
)
