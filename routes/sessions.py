import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.session import PlayerSession


router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)


class CreateSessionRequest(BaseModel):
    user_id: int
    device_type: str = Field(min_length=1, max_length=50)
    platform: str = Field(min_length=1, max_length=50)
    quality_mode: str = Field(default="AUTO", max_length=20)
    city_id: int | None = None
    district_id: int | None = None


class UpdateSessionRequest(BaseModel):
    quality_mode: str | None = Field(default=None, max_length=20)
    city_id: int | None = None
    district_id: int | None = None


@router.post("/create")
async def create_session(
    data: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    session_token = secrets.token_urlsafe(48)

    session = PlayerSession(
        user_id=data.user_id,
        session_token=session_token,
        device_type=data.device_type,
        platform=data.platform,
        quality_mode=data.quality_mode,
        city_id=data.city_id,
        district_id=data.district_id,
        online=True,
        connected_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
    )

    db.add(session)

    await db.commit()
    await db.refresh(session)

    return {
        "status": "session_created",
        "session": {
            "id": session.id,
            "session_token": session.session_token,
            "user_id": session.user_id,
            "device_type": session.device_type,
            "platform": session.platform,
            "quality_mode": session.quality_mode,
            "city_id": session.city_id,
            "district_id": session.district_id,
            "online": session.online,
        },
    }


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerSession).where(
            PlayerSession.id == session_id
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return {
        "id": session.id,
        "user_id": session.user_id,
        "device_type": session.device_type,
        "platform": session.platform,
        "quality_mode": session.quality_mode,
        "city_id": session.city_id,
        "district_id": session.district_id,
        "online": session.online,
        "connected_at": session.connected_at,
        "last_activity": session.last_activity,
        "disconnected_at": session.disconnected_at,
    }


@router.patch("/{session_id}")
async def update_session(
    session_id: int,
    data: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerSession).where(
            PlayerSession.id == session_id
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    if data.quality_mode is not None:
        session.quality_mode = data.quality_mode

    if data.city_id is not None:
        session.city_id = data.city_id

    if data.district_id is not None:
        session.district_id = data.district_id

    session.last_activity = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return {
        "status": "session_updated",
        "session": {
            "id": session.id,
            "quality_mode": session.quality_mode,
            "city_id": session.city_id,
            "district_id": session.district_id,
            "online": session.online,
            "last_activity": session.last_activity,
        },
    }


@router.post("/{session_id}/heartbeat")
async def heartbeat(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerSession).where(
            PlayerSession.id == session_id
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    session.online = True
    session.last_activity = datetime.utcnow()

    await db.commit()

    return {
        "status": "heartbeat_received",
        "session_id": session.id,
        "online": True,
        "last_activity": session.last_activity,
    }


@router.post("/{session_id}/disconnect")
async def disconnect_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerSession).where(
            PlayerSession.id == session_id
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    session.online = False
    session.disconnected_at = datetime.utcnow()
    session.last_activity = datetime.utcnow()

    await db.commit()

    return {
        "status": "session_disconnected",
        "session_id": session.id,
        "online": False,
    }
