from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    required_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    reward_money: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    reward_experience: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    reward_reputation: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    max_players: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class EventParticipant(Base):
    __tablename__ = "event_participants"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    event_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    reward_claimed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
)
