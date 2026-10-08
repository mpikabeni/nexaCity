from fastapi import APIRouter, Depends, HTTPException
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
        max_length=100,
    )


class OnlineStatusRequest(BaseModel):
    online: bool


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
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
        "active": user.active,
        "online": user.online,
        "created_at": user.created_at,
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if data.language is not None:
        user.language = data.language

    if data.country is not None:
        user.country = data.country

    await db.commit()
    await db.refresh(user)

    return {
        "status": "user_updated",
        "user": {
            "id": user.id,
            "language": user.language,
            "country": user.country,
        },
    }


@router.post("/{user_id}/status")
async def update_online_status(
    user_id: int,
    data: OnlineStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.online = data.online

    await db.commit()

    return {
        "status": "online_status_updated",
        "user_id": user.id,
        "online": user.online,
}
