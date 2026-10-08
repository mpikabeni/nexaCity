from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ============================================================
# SCHEMAS
# ============================================================

class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        max_length=100,
    )
    first_name: str | None = Field(
        default=None,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
    )
    language: str | None = Field(
        default=None,
        max_length=20,
    )
    country: str | None = Field(
        default=None,
        max_length=100,
    )


class UserStatusUpdate(BaseModel):
    online: bool


# ============================================================
# SERIALIZER
# ============================================================

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
# MY PROFILE
# ============================================================

@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Retourne le profil du joueur actuellement connecté.
    """

    return {
        "status": "success",
        "user": serialize_user(current_user),
    }


# ============================================================
# UPDATE MY PROFILE
# ============================================================

@router.patch("/me")
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Modifie uniquement le profil du joueur connecté.
    """

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    # --------------------------------------------------------
    # USERNAME
    # --------------------------------------------------------

    if "username" in updates:

        username = updates["username"].strip()

        if username:

            result = await db.execute(
                select(User).where(
                    User.username == username,
                    User.id != current_user.id,
                )
            )

            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=409,
                    detail="Ce nom d'utilisateur est déjà utilisé.",
                )

            current_user.username = username

    # --------------------------------------------------------
    # PRENOM
    # --------------------------------------------------------

    if "first_name" in updates:
        current_user.first_name = (
            updates["first_name"].strip()
        )

    # --------------------------------------------------------
    # NOM
    # --------------------------------------------------------

    if "last_name" in updates:
        current_user.last_name = (
            updates["last_name"].strip()
        )

    # --------------------------------------------------------
    # LANGUE
    # --------------------------------------------------------

    if "language" in updates:

        language = updates["language"].strip()

        if language:
            current_user.language = language

    # --------------------------------------------------------
    # PAYS
    # --------------------------------------------------------

    if "country" in updates:

        country = updates["country"].strip()

        if country:
            current_user.country = country

    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return {
        "status": "success",
        "message": "Profil mis à jour.",
        "user": serialize_user(current_user),
    }


# ============================================================
# MY ONLINE STATUS
# ============================================================

@router.patch("/me/status")
async def update_my_status(
    data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Met à jour le statut en ligne du joueur connecté.
    """

    current_user.online = data.online
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "user_id": current_user.id,
        "online": current_user.online,
        "updated_at": current_user.updated_at,
    }


# ============================================================
# DEACTIVATE MY ACCOUNT
# ============================================================

@router.post("/me/deactivate")
async def deactivate_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Désactive le compte du joueur connecté.
    """

    current_user.active = False
    current_user.online = False
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "Compte désactivé.",
    }


# ============================================================
# PUBLIC USER PROFILE
# ============================================================

@router.get("/{user_id}/public")
async def get_public_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne uniquement les informations publiques
    d'un autre joueur.

    Cette route ne donne jamais :
    - telegram_id
    - données privées
    - informations sensibles
    """

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.active.is_(True),
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Joueur introuvable.",
        )

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role,
            "online": user.online,
            "created_at": user.created_at,
        },
}
