from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    device_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    platform: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    operating_system: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    gpu: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    webgl_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    screen_width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    screen_height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pixel_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    quality_mode: Mapped[str] = mapped_column(
        String(20),
        default="AUTO",
        nullable=False,
    )

    fps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    battery_level: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    is_low_power: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
