from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.business import Business
from models.character import Character
from models.property import Property
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"],
)


# ============================================================
# SCHEMAS
# ============================================================

class BusinessCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    business_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
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

    capital: float = Field(
        ...,
        gt=0,
    )

    property_id: int | None = Field(
        default=None,
        gt=0,
    )


class BusinessUpgrade(BaseModel):
    price: float = Field(
        ...,
        gt=0,
    )


class BusinessStatusUpdate(BaseModel):
    is_open: bool


# ============================================================
# SERIALIZER
# ============================================================

def serialize_business(
    business: Business,
) -> dict:

    return {
        "id": business.id,
        "owner_id": business.owner_id,
        "property_id": business.property_id,

        "name": business.name,
        "business_type": business.business_type,
        "description": business.description,

        "location": {
            "city": business.city,
            "district": business.district,
        },

        "level": business.level,
        "reputation": business.reputation,

        "capital": business.capital,
        "revenue": business.revenue,

        "employees_count": business.employees_count,

        "is_open": business.is_open,

        "created_at": business.created_at,
        "updated_at": business.updated_at,
    }


# ============================================================
# MY BUSINESSES
# ============================================================

@router.get("/me")
async def get_my_businesses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business)
        .where(
            Business.owner_id == current_user.id
        )
        .order_by(
            Business.created_at.asc()
        )
    )

    businesses = result.scalars().all()

    return {
        "status": "success",
        "businesses": [
            serialize_business(business)
            for business in businesses
        ],
    }


# ============================================================
# GET BUSINESS
# ============================================================

@router.get("/me/{business_id}")
async def get_my_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(
            Business.id == business_id,
            Business.owner_id == current_user.id,
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable.",
        )

    return {
        "status": "success",
        "business": serialize_business(business),
    }


# ============================================================
# CREATE BUSINESS
# ============================================================

@router.post("/me")
async def create_business(
    data: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Création d'une entreprise virtuelle.
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
            detail="Un personnage mort ne peut pas créer une entreprise.",
        )

    # --------------------------------------------------------
    # VERIFICATION DE LA PROPRIETE
    # --------------------------------------------------------

    if data.property_id is not None:

        property_result = await db.execute(
            select(Property).where(
                Property.id == data.property_id,
                Property.owner_id == current_user.id,
                Property.owned.is_(True),
            )
        )

        property = property_result.scalar_one_or_none()

        if not property:
            raise HTTPException(
                status_code=403,
                detail="Cette propriété ne vous appartient pas.",
            )

    # --------------------------------------------------------
    # CAPITAL
    # --------------------------------------------------------

    capital = Decimal(str(data.capital))
    balance = Decimal(str(character.money))

    if balance < capital:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant pour créer cette entreprise.",
        )

    # --------------------------------------------------------
    # DEBIT
    # --------------------------------------------------------

    character.money = float(
        balance - capital
    )

    # --------------------------------------------------------
    # CREATION
    # --------------------------------------------------------

    business = Business(
        owner_id=current_user.id,
        property_id=data.property_id,

        name=data.name,
        business_type=data.business_type,
        description=data.description,

        city=data.city,
        district=data.district,

        level=1,
        reputation=0,

        capital=float(capital),
        revenue=0,

        employees_count=0,

        is_open=True,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(business)

    await db.commit()
    await db.refresh(business)

    return {
        "status": "success",
        "message": "Entreprise créée avec succès.",

        "business": serialize_business(
            business
        ),

        "remaining_balance": character.money,
    }


# ============================================================
# UPGRADE BUSINESS
# ============================================================

@router.post("/me/{business_id}/upgrade")
async def upgrade_business(
    business_id: int,
    data: BusinessUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(
            Business.id == business_id,
            Business.owner_id == current_user.id,
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable.",
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
            detail="Un personnage mort ne peut pas améliorer une entreprise.",
        )

    price = Decimal(str(data.price))
    balance = Decimal(str(character.money))

    if balance < price:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    character.money = float(
        balance - price
    )

    business.level += 1

    business.capital = float(
        Decimal(str(business.capital))
        + price
    )

    business.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(business)

    return {
        "status": "success",
        "message": "Entreprise améliorée.",

        "business": serialize_business(
            business
        ),

        "remaining_balance": character.money,
    }


# ============================================================
# BUSINESS REVENUE
# ============================================================

@router.get("/me/{business_id}/revenue")
async def get_business_revenue(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(
            Business.id == business_id,
            Business.owner_id == current_user.id,
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable.",
        )

    return {
        "status": "success",

        "business_id": business.id,
        "name": business.name,

        "capital": business.capital,
        "revenue": business.revenue,

        "level": business.level,
        "reputation": business.reputation,

        "employees_count": business.employees_count,
        "is_open": business.is_open,
    }


# ============================================================
# CHANGE BUSINESS STATUS
# ============================================================

@router.patch("/me/{business_id}/status")
async def update_business_status(
    business_id: int,
    data: BusinessStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(
            Business.id == business_id,
            Business.owner_id == current_user.id,
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable.",
        )

    business.is_open = data.is_open
    business.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(business)

    return {
        "status": "success",
        "message": "Statut de l'entreprise mis à jour.",
        "business": serialize_business(
            business
        ),
    }


# ============================================================
# PUBLIC BUSINESS
# ============================================================

@router.get("/{business_id}/public")
async def get_public_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Business).where(
            Business.id == business_id
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable.",
        )

    return {
        "status": "success",

        "business": {
            "id": business.id,

            "name": business.name,
            "business_type": business.business_type,
            "description": business.description,

            "city": business.city,
            "district": business.district,

            "level": business.level,
            "reputation": business.reputation,

            "employees_count": business.employees_count,
            "is_open": business.is_open,
        },
}
