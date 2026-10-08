from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.event import Event, EventParticipant
from services.auth_dependencies import get_current_user
from models.user import User


router = APIRouter(prefix="/events", tags=["Events"])


class EventCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    event_type: str = Field(default="WORLD", max_length=50)

    city: Optional[str] = None
    district: Optional[str] = None

    max_participants: Optional[int] = Field(default=None, ge=1)

    reward_money: float = Field(default=0, ge=0)
    reward_experience: float = Field(default=0, ge=0)
    reward_reputation: float = Field(default=0, ge=0)

    starts_at: datetime
    ends_at: datetime


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    event_type: str
    city: Optional[str]
    district: Optional[str]
    max_participants: Optional[int]

    reward_money: float
    reward_experience: float
    reward_reputation: float

    starts_at: datetime
    ends_at: datetime
    active: bool


class JoinEventResponse(BaseModel):
    status: str
    event_id: int
    user_id: int


def event_to_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        city=event.city,
        district=event.district,
        max_participants=event.max_participants,
        reward_money=float(event.reward_money or 0),
        reward_experience=float(event.reward_experience or 0),
        reward_reputation=float(event.reward_reputation or 0),
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        active=event.active,
    )


@router.get("", response_model=list[EventResponse])
async def list_events(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).order_by(desc(Event.starts_at))

    if active_only:
        query = query.where(Event.active.is_(True))

    result = await db.execute(query)
    events = result.scalars().all()

    return [event_to_response(event) for event in events]


@router.get("/upcoming", response_model=list[EventResponse])
async def upcoming_events(
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Event)
        .where(
            Event.active.is_(True),
            Event.starts_at >= now,
        )
        .order_by(Event.starts_at.asc())
    )

    events = result.scalars().all()

    return [event_to_response(event) for event in events]


@router.get("/me")
async def my_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventParticipant, Event)
        .join(Event, Event.id == EventParticipant.event_id)
        .where(EventParticipant.user_id == current_user.id)
        .order_by(desc(Event.starts_at))
    )

    rows = result.all()

    return [
        {
            "event": event_to_response(event),
            "participation": {
                "id": participant.id,
                "status": participant.status,
                "joined_at": participant.joined_at,
            },
        }
        for participant, event in rows
    ]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )

    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Événement introuvable.",
        )

    return event_to_response(event)


@router.post("/{event_id}/join", response_model=JoinEventResponse)
async def join_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )

    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Événement introuvable.",
        )

    now = datetime.now(timezone.utc)

    if not event.active:
        raise HTTPException(
            status_code=400,
            detail="Cet événement n'est plus actif.",
        )

    if event.ends_at <= now:
        raise HTTPException(
            status_code=400,
            detail="Cet événement est terminé.",
        )

    existing_result = await db.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == current_user.id,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.status == "JOINED":
            raise HTTPException(
                status_code=400,
                detail="Vous participez déjà à cet événement.",
            )

        existing.status = "JOINED"

        await db.commit()

        return JoinEventResponse(
            status="joined",
            event_id=event_id,
            user_id=current_user.id,
        )

    if event.max_participants is not None:
        count_result = await db.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.status == "JOINED",
            )
        )

        participants = count_result.scalars().all()

        if len(participants) >= event.max_participants:
            raise HTTPException(
                status_code=400,
                detail="L'événement est complet.",
            )

    participant = EventParticipant(
        event_id=event_id,
        user_id=current_user.id,
        status="JOINED",
        joined_at=now,
    )

    db.add(participant)

    await db.commit()

    return JoinEventResponse(
        status="joined",
        event_id=event_id,
        user_id=current_user.id,
    )


@router.post("/{event_id}/leave")
async def leave_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == current_user.id,
        )
    )

    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Vous ne participez pas à cet événement.",
        )

    participant.status = "LEFT"

    await db.commit()

    return {
        "status": "left",
        "event_id": event_id,
    }


@router.get("/{event_id}/participants")
async def event_participants(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    event_result = await db.execute(
        select(Event).where(Event.id == event_id)
    )

    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Événement introuvable.",
        )

    result = await db.execute(
        select(EventParticipant, User)
        .join(User, User.id == EventParticipant.user_id)
        .where(
            EventParticipant.event_id == event_id,
            EventParticipant.status == "JOINED",
        )
        .order_by(EventParticipant.joined_at.asc())
    )

    rows = result.all()

    return [
        {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "joined_at": participant.joined_at,
        }
        for participant, user in rows
]
