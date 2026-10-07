from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Election(Base):
    __tablename__ = "elections"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    election_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    required_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class ElectionCandidate(Base):
    __tablename__ = "election_candidates"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    election_id: Mapped[int] = mapped_column(
        ForeignKey("elections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    campaign_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    votes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class ElectionVote(Base):
    __tablename__ = "election_votes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    election_id: Mapped[int] = mapped_column(
        ForeignKey("elections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("election_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    voter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
)
