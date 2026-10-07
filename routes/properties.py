from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.property_service import PropertyService


router = APIRouter(
    prefix="/properties",
    tags=["Properties"],
)


class BuyPropertyRequest(BaseModel):
    user_id: int
    property_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)


class UpgradePropertyRequest(BaseModel):
    user_id: int
    property_id: int
    cost: float = Field(gt=0)


@router.get("/{user_id}")
async def get_player_properties(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    properties = await PropertyService.get_player_properties(
        db,
        user_id,
    )

    return {
        "user_id": user_id,
        "properties": [
            {
                "id": prop.id,
                "property_type": prop.property_type,
                "name": prop.name,
                "city": prop.city,
                "district": prop.district,
                "address": prop.address,
                "purchase_price": prop.purchase_price,
                "current_value": prop.current_value,
                "level": prop.level,
                "owned": prop.owned,
            }
            for prop in properties
        ],
    }


@router.get("/{user_id}/{property_id}")
async def get_property(
    user_id: int,
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    prop = await PropertyService.get_property(
        db,
        user_id,
        property_id,
    )

    if prop is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found",
        )

    return {
        "id": prop.id,
        "property_type": prop.property_type,
        "name": prop.name,
        "city": prop.city,
        "district": prop.district,
        "address": prop.address,
        "purchase_price": prop.purchase_price,
        "current_value": prop.current_value,
        "level": prop.level,
        "owned": prop.owned,
    }


@router.post("/buy")
async def buy_property(
    data: BuyPropertyRequest,
    db: AsyncSession = Depends(get_db),
):
    prop = await PropertyService.buy_property(
        db=db,
        user_id=data.user_id,
        property_type=data.property_type,
        name=data.name,
        city=data.city,
        district=data.district,
        address=data.address,
        price=data.price,
    )

    if prop is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to purchase property",
        )

    return {
        "status": "property_purchased",
        "property": {
            "id": prop.id,
            "property_type": prop.property_type,
            "name": prop.name,
            "city": prop.city,
            "district": prop.district,
            "address": prop.address,
            "purchase_price": prop.purchase_price,
            "current_value": prop.current_value,
            "level": prop.level,
            "owned": prop.owned,
        },
    }


@router.post("/upgrade")
async def upgrade_property(
    data: UpgradePropertyRequest,
    db: AsyncSession = Depends(get_db),
):
    prop = await PropertyService.upgrade_property(
        db=db,
        user_id=data.user_id,
        property_id=data.property_id,
        cost=data.cost,
    )

    if prop is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to upgrade property",
        )

    return {
        "status": "property_upgraded",
        "property": {
            "id": prop.id,
            "level": prop.level,
            "current_value": prop.current_value,
        },
}
