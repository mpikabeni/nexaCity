from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.user import User


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


class UpdateUserRequest(BaseModel):
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )

    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language": user.language,
        "country": user.country,
        "role": user.role,
        "is_online": user.is_online,
        "created_at": user.created_at,
        "last_seen": user.last_seen,
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if data.language is not None:
        user.language = data.language

    if data.country is not None:
        user.country = data.country

    user.last_seen = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return {
        "status": "updated",
        "user": {
            "id": user.id,
            "language": user.language,
            "country": user.country,
        },
    }


@router.post("/{user_id}/online")
async def set_online(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_online = True
    user.last_seen = datetime.utcnow()

    await db.commit()

    return {
        "status": "online",
    }


@router.post("/{user_id}/offline")
async def set_offline(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_online = False
    user.last_seen = datetime.utcnow()

    await db.commit()

    return {
        "status": "offline",
}
