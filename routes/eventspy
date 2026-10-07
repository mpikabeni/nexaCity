from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.event import Event, EventParticipant


router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=1000)
    event_type: str = Field(min_length=1, max_length=50)
    city: str | None = None
    district: str | None = None
    starts_at: datetime
    ends_at: datetime
    max_participants: int | None = Field(default=None, gt=0)
    reward_money: float = Field(default=0, ge=0)
    reward_xp: int = Field(default=0, ge=0)
    reward_reputation: int = Field(default=0, ge=0)


class JoinEventRequest(BaseModel):
    user_id: int
    event_id: int


@router.get("/")
async def get_events(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).order_by(Event.starts_at.asc())

    if active_only:
        query = query.where(Event.is_active == True)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "city": event.city,
                "district": event.district,
                "starts_at": event.starts_at,
                "ends_at": event.ends_at,
                "max_participants": event.max_participants,
                "reward_money": event.reward_money,
                "reward_xp": event.reward_xp,
                "reward_reputation": event.reward_reputation,
                "is_active": event.is_active,
            }
            for event in events
        ]
    }


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )

    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type,
        "city": event.city,
        "district": event.district,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "max_participants": event.max_participants,
        "reward_money": event.reward_money,
        "reward_xp": event.reward_xp,
        "reward_reputation": event.reward_reputation,
        "is_active": event.is_active,
    }


@router.post("/join")
async def join_event(
    data: JoinEventRequest,
    db: AsyncSession = Depends(get_db),
):
    event_result = await db.execute(
        select(Event).where(Event.id == data.event_id)
    )

    event = event_result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    if not event.is_active:
        raise HTTPException(
            status_code=400,
            detail="Event is not active",
        )

    now = datetime.utcnow()

    if now < event.starts_at:
        raise HTTPException(
            status_code=400,
            detail="Event has not started yet",
        )

    if now > event.ends_at:
        raise HTTPException(
            status_code=400,
            detail="Event has already ended",
        )

    existing_result = await db.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == data.event_id,
            EventParticipant.user_id == data.user_id,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Player already joined this event",
        )

    if event.max_participants is not None:
        count_result = await db.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == data.event_id
            )
        )

        participants = count_result.scalars().all()

        if len(participants) >= event.max_participants:
            raise HTTPException(
                status_code=400,
                detail="Event is full",
            )

    participant = EventParticipant(
        event_id=data.event_id,
        user_id=data.user_id,
        score=0,
        completed=False,
    )

    db.add(participant)

    await db.commit()
    await db.refresh(participant)

    return {
        "status": "event_joined",
        "event_id": data.event_id,
        "user_id": data.user_id,
        "participant_id": participant.id,
    }


@router.get("/{event_id}/participants")
async def get_event_participants(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventParticipant)
        .where(EventParticipant.event_id == event_id)
        .order_by(EventParticipant.score.desc())
    )

    participants = result.scalars().all()

    return {
        "event_id": event_id,
        "participants": [
            {
                "id": participant.id,
                "user_id": participant.user_id,
                "score": participant.score,
                "completed": participant.completed,
            }
            for participant in participants
        ],
}
