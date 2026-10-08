from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.property import Property
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/properties",
    tags=["Properties"],
)


# ============================================================
# SCHEMAS
# ============================================================

class PropertyPurchase(BaseModel):
    property_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    city: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    district: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    address: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    price: float = Field(
        ...,
        gt=0,
    )


class PropertyUpgrade(BaseModel):
    price: float = Field(
        ...,
        gt=0,
    )


# ============================================================
# SERIALIZER
# ============================================================

def serialize_property(property: Property) -> dict:
    return {
        "id": property.id,
        "owner_id": property.owner_id,

        "property_type": property.property_type,
        "name": property.name,

        "location": {
            "city": property.city,
            "district": property.district,
            "address": property.address,
        },

        "purchase_price": property.purchase_price,
        "current_value": property.current_value,

        "level": property.level,
        "owned": property.owned,

        "created_at": property.created_at,
        "updated_at": property.updated_at,
    }


# ============================================================
# MY PROPERTIES
# ============================================================

@router.get("/me")
async def get_my_properties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property)
        .where(
            Property.owner_id == current_user.id
        )
        .order_by(
            Property.created_at.asc()
        )
    )

    properties = result.scalars().all()

    return {
        "status": "success",
        "properties": [
            serialize_property(property)
            for property in properties
        ],
    }


# ============================================================
# GET PROPERTY
# ============================================================

@router.get("/me/{property_id}")
async def get_my_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.owner_id == current_user.id,
        )
    )

    property = result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=404,
            detail="Propriété introuvable.",
        )

    return {
        "status": "success",
        "property": serialize_property(property),
    }


# ============================================================
# BUY PROPERTY
# ============================================================

@router.post("/me/buy")
async def buy_property(
    data: PropertyPurchase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Achète une propriété avec la monnaie virtuelle du jeu.
    """

    character_result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = character_result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Personnage introuvable.",
        )

    if not character.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Un personnage mort ne peut pas acheter une propriété.",
        )

    price = Decimal(str(data.price))
    balance = Decimal(str(character.money))

    if balance < price:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    # --------------------------------------------------------
    # DEBIT DU JOUEUR
    # --------------------------------------------------------

    character.money = float(
        balance - price
    )

    # --------------------------------------------------------
    # CREATION DE LA PROPRIETE
    # --------------------------------------------------------

    property = Property(
        owner_id=current_user.id,

        property_type=data.property_type,
        name=data.name,

        city=data.city,
        district=data.district,
        address=data.address,

        purchase_price=float(price),
        current_value=float(price),

        level=1,
        owned=True,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(property)

    await db.commit()
    await db.refresh(property)

    return {
        "status": "success",
        "message": "Propriété achetée avec succès.",

        "property": serialize_property(property),

        "remaining_balance": character.money,
    }


# ============================================================
# UPGRADE PROPERTY
# ============================================================

@router.post("/me/{property_id}/upgrade")
async def upgrade_property(
    property_id: int,
    data: PropertyUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Améliore une propriété.
    """

    property_result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.owner_id == current_user.id,
        )
    )

    property = property_result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=404,
            detail="Propriété introuvable.",
        )

    character_result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = character_result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Personnage introuvable.",
        )

    if not character.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Un personnage mort ne peut pas améliorer une propriété.",
        )

    price = Decimal(str(data.price))
    balance = Decimal(str(character.money))

    if balance < price:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    # --------------------------------------------------------
    # DEBIT
    # --------------------------------------------------------

    character.money = float(
        balance - price
    )

    # --------------------------------------------------------
    # UPGRADE
    # --------------------------------------------------------

    property.level += 1

    property.current_value = float(
        Decimal(str(property.current_value))
        + price
    )

    property.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(property)

    return {
        "status": "success",
        "message": "Propriété améliorée.",

        "property": serialize_property(property),

        "remaining_balance": character.money,
    }


# ============================================================
# PUBLIC PROPERTY
# ============================================================

@router.get("/{property_id}/public")
async def get_public_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Informations publiques d'une propriété.
    """

    result = await db.execute(
        select(Property).where(
            Property.id == property_id
        )
    )

    property = result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=404,
            detail="Propriété introuvable.",
        )

    return {
        "status": "success",
        "property": {
            "id": property.id,
            "property_type": property.property_type,
            "name": property.name,

            "city": property.city,
            "district": property.district,

            "level": property.level,
            "current_value": property.current_value,

            "owned": property.owned,
        },
}
