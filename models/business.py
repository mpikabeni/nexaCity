from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    business_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    reputation: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    capital: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    revenue: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    employees_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
