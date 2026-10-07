from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.connection import get_db
from models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class TelegramAuthRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language: str | None = None


def create_access_token(user_id: int) -> str:
    expires_at = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/telegram")
async def authenticate_telegram(
    data: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    if data.telegram_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Telegram ID",
        )

    result = await db.execute(
        select(User).where(
            User.telegram_id == data.telegram_id
        )
    )

    user = result.scalar_one_or_none()

    is_new_player = False

    if user is None:
        user = User(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            language=data.language or "en",
            role="PLAYER",
            is_active=True,
            is_online=True,
            last_seen=datetime.utcnow(),
        )

        db.add(user)

        await db.commit()
        await db.refresh(user)

        is_new_player = True

    else:
        user.username = data.username
        user.first_name = data.first_name
        user.last_name = data.last_name

        if data.language:
            user.language = data.language

        user.is_active = True
        user.is_online = True
        user.last_seen = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language": user.language,
            "role": user.role,
        },
        "is_new_player": is_new_player,
    }


@router.post("/logout")
async def logout(
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_online = False
    user.last_seen = datetime.utcnow()

    await db.commit()

    return {
        "status": "logged_out",
}
