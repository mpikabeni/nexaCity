from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.user import User
from services.auth_dependencies import get_current_user


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

    skin_tone: str = Field(
        default="default",
        max_length=50,
    )

    hairstyle: str = Field(
        default="default",
        max_length=50,
    )

    eye_style: str = Field(
        default="default",
        max_length=50,
    )

    outfit: str = Field(
        default="default",
        max_length=50,
    )

    shoes: str = Field(
        default="default",
        max_length=50,
    )

    accessories: str | None = Field(
        default=None,
        max_length=500,
    )


class CharacterUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
    )

    gender: str | None = Field(
        default=None,
        max_length=20,
    )

    skin_tone: str | None = Field(
        default=None,
        max_length=50,
    )

    hairstyle: str | None = Field(
        default=None,
        max_length=50,
    )

    eye_style: str | None = Field(
        default=None,
        max_length=50,
    )

    outfit: str | None = Field(
        default=None,
        max_length=50,
    )

    shoes: str | None = Field(
        default=None,
        max_length=50,
    )

    accessories: str | None = Field(
        default=None,
        max_length=500,
    )


# ============================================================
# SERIALIZER
# ============================================================

def serialize_character(
    character: Character,
) -> dict:

    return {
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
    }


# ============================================================
# GET MY CHARACTER
# ============================================================

@router.get("/me")
async def get_my_character(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Récupère le personnage du joueur connecté.
    """

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Aucun personnage créé.",
        )

    return {
        "status": "success",
        "character": serialize_character(character),
    }


# ============================================================
# CREATE MY CHARACTER
# ============================================================

@router.post("/me")
async def create_my_character(
    data: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crée le personnage principal du joueur connecté.

    Un joueur ne peut avoir qu'un seul personnage.
    """

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    existing_character = result.scalar_one_or_none()

    if existing_character:
        raise HTTPException(
            status_code=409,
            detail="Vous possédez déjà un personnage.",
        )

    character = Character(
        user_id=current_user.id,

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
        "character": serialize_character(character),
    }


# ============================================================
# UPDATE MY CHARACTER
# ============================================================

@router.patch("/me")
async def update_my_character(
    data: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Modifie les éléments personnalisables du personnage.
    """

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Aucun personnage créé.",
        )

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in updates.items():

        if hasattr(character, field):
            setattr(
                character,
                field,
                value,
            )

    character.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(character)

    return {
        "status": "success",
        "message": "Personnage mis à jour.",
        "character": serialize_character(character),
    }


# ============================================================
# CHARACTER STATUS
# ============================================================

@router.get("/me/status")
async def get_my_character_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les données nécessaires au jeu en temps réel.
    """

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Aucun personnage créé.",
        )

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
# SYNC CHARACTER
# ============================================================

@router.post("/me/sync")
async def sync_my_character(
    data: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronisation du personnage.

    Le frontend pourra appeler cette route :
    - après une action importante ;
    - lors d'une sauvegarde périodique ;
    - avant la fermeture de la session.
    """

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Aucun personnage créé.",
        )

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in updates.items():

        if hasattr(character, field):
            setattr(
                character,
                field,
                value,
            )

    character.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(character)

    return {
        "status": "success",
        "message": "Personnage synchronisé.",
        "character_id": character.id,
        "updated_at": character.updated_at,
    }


# ============================================================
# PUBLIC CHARACTER
# ============================================================

@router.get("/{character_id}/public")
async def get_public_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Profil public d'un autre joueur.
    """

    result = await db.execute(
        select(Character).where(
            Character.id == character_id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Personnage introuvable.",
        )

    return {
        "status": "success",
        "character": {
            "id": character.id,
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
            "reputation": character.reputation,

            "is_alive": character.is_alive,

            "city": character.city,
            "district": character.district,
        },
    }money,

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
