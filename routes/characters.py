from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.user import User
from models.character import Character


router = APIRouter(
    prefix="/characters",
    tags=["Characters"],
)


# ============================================================
# SCHEMAS
# ============================================================

class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=30)
    gender: str = Field(..., min_length=1, max_length=20)

    skin_tone: str = Field(default="default", max_length=50)
    hairstyle: str = Field(default="default", max_length=50)
    eye_style: str = Field(default="default", max_length=50)
    outfit: str = Field(default="default", max_length=50)
    shoes: str = Field(default="default", max_length=50)
    accessories: Optional[str] = Field(default=None, max_length=500)


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=30)
    gender: Optional[str] = Field(default=None, max_length=20)

    skin_tone: Optional[str] = Field(default=None, max_length=50)
    hairstyle: Optional[str] = Field(default=None, max_length=50)
    eye_style: Optional[str] = Field(default=None, max_length=50)
    outfit: Optional[str] = Field(default=None, max_length=50)
    shoes: Optional[str] = Field(default=None, max_length=50)
    accessories: Optional[str] = Field(default=None, max_length=500)

    city: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)


# ============================================================
# HELPERS
# ============================================================

async def get_user(
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
            detail="Utilisateur introuvable",
        )

    return user


async def get_character(
    user_id: int,
    db: AsyncSession,
) -> Character:
    result = await db.execute(
        select(Character).where(Character.user_id == user_id)
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Personnage introuvable",
        )

    return character


# ============================================================
# CREATE CHARACTER
# ============================================================

@router.post("/{user_id}")
async def create_character(
    user_id: int,
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée le personnage principal d'un joueur.

    Un utilisateur ne peut posséder qu'un seul personnage principal.
    """

    await get_user(user_id, db)

    existing_result = await db.execute(
        select(Character).where(Character.user_id == user_id)
    )

    existing_character = existing_result.scalar_one_or_none()

    if existing_character:
        raise HTTPException(
            status_code=409,
            detail="Ce joueur possède déjà un personnage.",
        )

    character = Character(
        user_id=user_id,

        name=data.name,
        gender=data.gender,

        skin_tone=data.skin_tone,
        hairstyle=data.hairstyle,
        eye_style=data.eye_style,
        outfit=data.outfit,
        shoes=data.shoes,
        accessories=data.accessories,

        level=1,
        experience=0,
        reputation=0,
        money=0,

        energy=100,
        hunger=100,
        hydration=100,
        health=100,

        is_alive=True,
        respawn_at=None,

        city=None,
        district=None,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(character)

    await db.commit()
    await db.refresh(character)

    return {
        "status": "success",
        "message": "Personnage créé avec succès.",
        "character": {
            "id": character.id,
            "user_id": character.user_id,
            "name": character.name,
            "gender": character.gender,

            "appearance": {
                "skin_tone": character.skin_tone,
                "hairstyle": character.hairstyle,
                "eye_style": character.eye_style,
                "outfit": character.outfit,
                "shoes": character.shoes,
                "accessories": character.accessories,
            },

            "level": character.level,
            "experience": character.experience,
            "reputation": character.reputation,
            "money": character.money,

            "needs": {
                "energy": character.energy,
                "hunger": character.hunger,
                "hydration": character.hydration,
                "health": character.health,
            },

            "is_alive": character.is_alive,
            "respawn_at": character.respawn_at,

            "city": character.city,
            "district": character.district,

            "created_at": character.created_at,
            "updated_at": character.updated_at,
        },
    }


# ============================================================
# GET CHARACTER
# ============================================================

@router.get("/{user_id}")
async def get_character_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne le personnage complet d'un joueur.
    """

    character = await get_character(user_id, db)

    return {
        "status": "success",
        "character": {
            "id": character.id,
            "user_id": character.user_id,

            "name": character.name,
            "gender": character.gender,

            "appearance": {
                "skin_tone": character.skin_tone,
                "hairstyle": character.hairstyle,
                "eye_style": character.eye_style,
                "outfit": character.outfit,
                "shoes": character.shoes,
                "accessories": character.accessories,
            },

            "progression": {
                "level": character.level,
                "experience": character.experience,
                "reputation": character.reputation,
            },

            "economy": {
                "money": character.money,
            },

            "needs": {
                "energy": character.energy,
                "hunger": character.hunger,
                "hydration": character.hydration,
                "health": character.health,
            },

            "life": {
                "is_alive": character.is_alive,
                "respawn_at": character.respawn_at,
            },

            "location": {
                "city": character.city,
                "district": character.district,
            },

            "created_at": character.created_at,
            "updated_at": character.updated_at,
        },
    }


# ============================================================
# UPDATE CHARACTER
# ============================================================

@router.patch("/{user_id}")
async def update_character(
    user_id: int,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Met à jour les informations personnalisables du personnage.
    """

    character = await get_character(user_id, db)

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in updates.items():

        # La position sera gérée par le système de localisation.
        if field in {"city", "district"}:
            setattr(character, field, value)
            continue

        if hasattr(character, field):
            setattr(character, field, value)

    character.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(character)

    return {
        "status": "success",
        "message": "Personnage mis à jour.",
        "character": {
            "id": character.id,
            "user_id": character.user_id,
            "name": character.name,
            "gender": character.gender,

            "appearance": {
                "skin_tone": character.skin_tone,
                "hairstyle": character.hairstyle,
                "eye_style": character.eye_style,
                "outfit": character.outfit,
                "shoes": character.shoes,
                "accessories": character.accessories,
            },

            "level": character.level,
            "experience": character.experience,
            "reputation": character.reputation,
            "money": character.money,

            "energy": character.energy,
            "hunger": character.hunger,
            "hydration": character.hydration,
            "health": character.health,

            "is_alive": character.is_alive,
            "respawn_at": character.respawn_at,

            "city": character.city,
            "district": character.district,

            "updated_at": character.updated_at,
        },
    }


# ============================================================
# CHARACTER STATUS
# ============================================================

@router.get("/{user_id}/status")
async def character_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne uniquement l'état important du personnage
    pour le jeu en temps réel.
    """

    character = await get_character(user_id, db)

    return {
        "status": "success",

        "character_id": character.id,
        "name": character.name,

        "level": character.level,
        "experience": character.experience,
        "reputation": character.reputation,

        "money": character.money,

        "energy": character.energy,
        "hunger": character.hunger,
        "hydration": character.hydration,
        "health": character.health,

        "is_alive": character.is_alive,
        "respawn_at": character.respawn_at,

        "city": character.city,
        "district": character.district,

        "updated_at": character.updated_at,
    }


# ============================================================
# SAVE CHARACTER STATE
# ============================================================

@router.post("/{user_id}/sync")
async def sync_character(
    user_id: int,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronisation du personnage.

    Utilisé par le jeu après certaines actions importantes
    et lors de la sauvegarde périodique.
    """

    character = await get_character(user_id, db)

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    allowed_fields = {
        "name",
        "gender",
        "skin_tone",
        "hairstyle",
        "eye_style",
        "outfit",
        "shoes",
        "accessories",
        "city",
        "district",
    }

    for field, value in updates.items():

        if field not in allowed_fields:
            continue

        if hasattr(character, field):
            setattr(character, field, value)

    character.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(character)

    return {
        "status": "success",
        "message": "État du personnage synchronisé.",
        "character_id": character.id,
        "updated_at": character.updated_at,
}
