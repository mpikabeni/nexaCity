from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character


router = APIRouter(
    prefix="/characters",
    tags=["Characters"],
)


class CreateCharacterRequest(BaseModel):
    user_id: int

    name: str = Field(
        min_length=2,
        max_length=50,
    )

    gender: str | None = Field(
        default=None,
        max_length=30,
    )

    skin_tone: str | None = Field(
        default=None,
        max_length=50,
    )

    hairstyle: str | None = Field(
        default=None,
        max_length=100,
    )

    eye_style: str | None = Field(
        default=None,
        max_length=100,
    )

    outfit: str | None = Field(
        default=None,
        max_length=100,
    )

    shoes: str | None = Field(
        default=None,
        max_length=100,
    )

    accessories: str | None = None


class UpdateCharacterRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    gender: str | None = Field(
        default=None,
        max_length=30,
    )

    skin_tone: str | None = Field(
        default=None,
        max_length=50,
    )

    hairstyle: str | None = Field(
        default=None,
        max_length=100,
    )

    eye_style: str | None = Field(
        default=None,
        max_length=100,
    )

    outfit: str | None = Field(
        default=None,
        max_length=100,
    )

    shoes: str | None = Field(
        default=None,
        max_length=100,
    )

    accessories: str | None = None


@router.post("/")
async def create_character(
    data: CreateCharacterRequest,
    db: AsyncSession = Depends(get_db),
):
    existing_result = await db.execute(
        select(Character).where(
            Character.user_id == data.user_id
        )
    )

    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character already exists",
        )

    character = Character(
        user_id=data.user_id,
        name=data.name.strip(),
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
        money=0.0,
        energy=100.0,
        hunger=100.0,
        hydration=100.0,
        health=100.0,
        is_alive=True,
    )

    db.add(character)

    await db.commit()
    await db.refresh(character)

    return {
        "status": "created",
        "character": {
            "id": character.id,
            "user_id": character.user_id,
            "name": character.name,
            "gender": character.gender,
            "skin_tone": character.skin_tone,
            "hairstyle": character.hairstyle,
            "eye_style": character.eye_style,
            "outfit": character.outfit,
            "shoes": character.shoes,
            "accessories": character.accessories,
            "level": character.level,
            "experience": character.experience,
            "reputation": character.reputation,
            "money": character.money,
            "energy": character.energy,
            "hunger": character.hunger,
            "hydration": character.hydration,
            "health": character.health,
            "is_alive": character.is_alive,
        },
    }


@router.get("/{user_id}")
async def get_character(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character).where(
            Character.user_id == user_id
        )
    )

    character = result.scalar_one_or_none()

    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return {
        "id": character.id,
        "user_id": character.user_id,
        "name": character.name,
        "gender": character.gender,
        "skin_tone": character.skin_tone,
        "hairstyle": character.hairstyle,
        "eye_style": character.eye_style,
        "outfit": character.outfit,
        "shoes": character.shoes,
        "accessories": character.accessories,
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
    }


@router.patch("/{user_id}")
async def update_character(
    user_id: int,
    data: UpdateCharacterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character).where(
            Character.user_id == user_id
        )
    )

    character = result.scalar_one_or_none()

    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    updates = data.model_dump(
        exclude_unset=True
    )

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()

        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)

    return {
        "status": "updated",
        "character": {
            "id": character.id,
            "name": character.name,
            "gender": character.gender,
            "skin_tone": character.skin_tone,
            "hairstyle": character.hairstyle,
            "eye_style": character.eye_style,
            "outfit": character.outfit,
            "shoes": character.shoes,
            "accessories": character.accessories,
        },
}
