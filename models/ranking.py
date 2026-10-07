from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class PlayerRanking(Base):
    __tablename__ = "player_rankings"

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

    global_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    level_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    reputation_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    wealth_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    mission_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    event_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    clan_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
