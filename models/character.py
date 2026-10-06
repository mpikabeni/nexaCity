from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Character(Base):
    __tablename__ = "characters"

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

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Apparence du personnage
    gender: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    skin_tone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    hairstyle: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    eye_style: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    outfit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    shoes: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    accessories: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Progression
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    experience: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    reputation: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Économie virtuelle
    money: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Besoins du personnage
    energy: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
    )

    hunger: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
    )

    hydration: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
    )

    health: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
    )

    # État du personnage
    is_alive: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    respawn_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Monde
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
)
