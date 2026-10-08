from datetime import datetime

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


# ============================================================
# SCHEMAS
# ============================================================

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)


class UserStatusUpdate(BaseModel):
    online: bool


# ============================================================
# HELPERS
# ============================================================

async def get_user_or_404(
    user_id: int,
    db: AsyncSession,
) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable.",
        )

    return user


def serialize_user(user: User) -> dict:
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
        "updated_at": user.updated_at,
    }


# ============================================================
# GET USER
# ============================================================

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(user_id, db)

    return {
        "status": "success",
        "user": serialize_user(user),
    }


# ============================================================
# UPDATE USER
# ============================================================

@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(user_id, db)

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    # Vérification du username
    if "username" in updates:
        username = updates["username"].strip()

        if username:
            result = await db.execute(
                select(User).where(
                    User.username == username,
                    User.id != user_id,
                )
            )

            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=409,
                    detail="Ce nom d'utilisateur est déjà utilisé.",
                )

            user.username = username

    if "first_name" in updates:
        user.first_name = updates["first_name"].strip()

    if "last_name" in updates:
        user.last_name = updates["last_name"].strip()

    if "language" in updates:
        user.language = updates["language"].strip()

    if "country" in updates:
        user.country = updates["country"].strip()

    user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "Profil utilisateur mis à jour.",
        "user": serialize_user(user),
    }


# ============================================================
# UPDATE ONLINE STATUS
# ============================================================

@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(user_id, db)

    user.online = data.online
    user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "user_id": user.id,
        "online": user.online,
        "updated_at": user.updated_at,
    }


# ============================================================
# DEACTIVATE ACCOUNT
# ============================================================

@router.post("/{user_id}/deactivate")
async def deactivate_account(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(user_id, db)

    user.active = False
    user.online = False
    user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "Compte désactivé.",
        "user_id": user.id,
    }


# ============================================================
# REACTIVATE ACCOUNT
# ============================================================

@router.post("/{user_id}/activate")
async def activate_account(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(user_id, db)

    user.active = True
    user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "Compte activé.",
        "user_id": user.id,
    }
