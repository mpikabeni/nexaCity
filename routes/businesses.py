from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.business_service import BusinessService


router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"],
)


class CreateBusinessRequest(BaseModel):
    user_id: int
    property_id: int
    name: str = Field(min_length=1, max_length=100)
    business_type: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=500)
    city: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    capital: float = Field(gt=0)


class UpgradeBusinessRequest(BaseModel):
    user_id: int
    business_id: int
    cost: float = Field(gt=0)


class RevenueRequest(BaseModel):
    business_id: int
    amount: float = Field(gt=0)


class BusinessStatusRequest(BaseModel):
    user_id: int
    business_id: int
    is_open: bool


@router.get("/{user_id}")
async def get_player_businesses(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    businesses = await BusinessService.get_player_businesses(
        db,
        user_id,
    )

    return {
        "user_id": user_id,
        "businesses": [
            {
                "id": business.id,
                "property_id": business.property_id,
                "name": business.name,
                "business_type": business.business_type,
                "description": business.description,
                "city": business.city,
                "district": business.district,
                "level": business.level,
                "reputation": business.reputation,
                "capital": business.capital,
                "revenue": business.revenue,
                "employees_count": business.employees_count,
                "is_open": business.is_open,
            }
            for business in businesses
        ],
    }


@router.get("/{user_id}/{business_id}")
async def get_business(
    user_id: int,
    business_id: int,
    db: AsyncSession = Depends(get_db),
):
    businesses = await BusinessService.get_player_businesses(
        db,
        user_id,
    )

    business = next(
        (item for item in businesses if item.id == business_id),
        None,
    )

    if business is None:
        raise HTTPException(
            status_code=404,
            detail="Business not found",
        )

    return {
        "id": business.id,
        "property_id": business.property_id,
        "name": business.name,
        "business_type": business.business_type,
        "description": business.description,
        "city": business.city,
        "district": business.district,
        "level": business.level,
        "reputation": business.reputation,
        "capital": business.capital,
        "revenue": business.revenue,
        "employees_count": business.employees_count,
        "is_open": business.is_open,
    }


@router.post("/create")
async def create_business(
    data: CreateBusinessRequest,
    db: AsyncSession = Depends(get_db),
):
    business = await BusinessService.create_business(
        db=db,
        user_id=data.user_id,
        property_id=data.property_id,
        name=data.name,
        business_type=data.business_type,
        description=data.description,
        city=data.city,
        district=data.district,
        capital=data.capital,
    )

    if business is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to create business",
        )

    return {
        "status": "business_created",
        "business": {
            "id": business.id,
            "property_id": business.property_id,
            "name": business.name,
            "business_type": business.business_type,
            "level": business.level,
            "capital": business.capital,
            "revenue": business.revenue,
            "is_open": business.is_open,
        },
    }


@router.post("/upgrade")
async def upgrade_business(
    data: UpgradeBusinessRequest,
    db: AsyncSession = Depends(get_db),
):
    business = await BusinessService.upgrade_business(
        db=db,
        user_id=data.user_id,
        business_id=data.business_id,
        cost=data.cost,
    )

    if business is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to upgrade business",
        )

    return {
        "status": "business_upgraded",
        "business": {
            "id": business.id,
            "level": business.level,
            "capital": business.capital,
        },
    }


@router.post("/revenue")
async def add_revenue(
    data: RevenueRequest,
    db: AsyncSession = Depends(get_db),
):
    business = await BusinessService.add_revenue(
        db=db,
        business_id=data.business_id,
        amount=data.amount,
    )

    if business is None:
        raise HTTPException(
            status_code=404,
            detail="Business not found",
        )

    return {
        "status": "revenue_added",
        "business_id": business.id,
        "revenue": business.revenue,
        "capital": business.capital,
    }


@router.patch("/status")
async def set_business_status(
    data: BusinessStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    business = await BusinessService.set_open_status(
        db=db,
        user_id=data.user_id,
        business_id=data.business_id,
        is_open=data.is_open,
    )

    if business is None:
        raise HTTPException(
            status_code=404,
            detail="Business not found",
        )

    return {
        "status": "business_status_updated",
        "business_id": business.id,
        "is_open": business.is_open,
}
