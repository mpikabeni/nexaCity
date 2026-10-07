from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
    )

    name_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    max_players: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
)
