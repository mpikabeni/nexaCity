import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
    init_data: str = Field(min_length=1)


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Vérifie cryptographiquement Telegram Web App initData.
    """

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid Telegram initData",
        )

    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise HTTPException(
            status_code=400,
            detail="Telegram hash missing",
        )

    auth_date = parsed.get("auth_date")

    if not auth_date:
        raise HTTPException(
            status_code=400,
            detail="Telegram auth_date missing",
        )

    try:
        auth_timestamp = int(auth_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid Telegram auth_date",
        )

    # Évite la réutilisation d'une ancienne initData.
    current_time = int(time.time())

    if current_time - auth_timestamp > 86400:
        raise HTTPException(
            status_code=401,
            detail="Telegram authentication data expired",
        )

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode(),
        hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        calculated_hash,
        received_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authentication",
        )

    user_data_raw = parsed.get("user")

    if not user_data_raw:
        raise HTTPException(
            status_code=400,
            detail="Telegram user data missing",
        )

    try:
        telegram_user = json.loads(user_data_raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid Telegram user data",
        )

    if not telegram_user.get("id"):
        raise HTTPException(
            status_code=400,
            detail="Telegram user ID missing",
        )

    return telegram_user


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(time.time()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/telegram")
async def telegram_login(
    data: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    telegram_user = verify_telegram_init_data(
        data.init_data
    )

    telegram_id = int(
        telegram_user["id"]
    )

    username = telegram_user.get(
        "username"
    )

    first_name = telegram_user.get(
        "first_name"
    )

    last_name = telegram_user.get(
        "last_name"
    )

    language = telegram_user.get(
        "language_code"
    )

    result = await db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    is_new_player = False

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            active=True,
            online=True,
        )

        db.add(user)

        await db.commit()
        await db.refresh(user)

        is_new_player = True

    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name

        if language:
            user.language = language

        user.active = True
        user.online = True

        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(
        user.id
    )

    return {
        "status": "authenticated",
        "is_new_player": is_new_player,
        "access_token": access_token,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language": user.language,
            "role": user.role,
        },
    }


@router.post("/logout/{user_id}")
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
            status_code=404,
            detail="User not found",
        )

    user.online = False

    await db.commit()

    return {
        "status": "logged_out",
        "user_id": user_id,
    }
