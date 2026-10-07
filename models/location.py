from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class PlayerLocation(Base):
    __tablename__ = "player_locations"

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

    city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    instance_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    position_x: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    position_y: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    position_z: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    rotation_y: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    last_synced_at: Mapped[datetime] = mapped_column(
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
