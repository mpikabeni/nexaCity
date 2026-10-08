from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.world import Country, City, District


router = APIRouter(
    prefix="/world",
    tags=["World"],
)


@router.get("/countries")
async def get_countries(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Country)
        .order_by(Country.name.asc())
    )

    countries = result.scalars().all()

    return {
        "countries": [
            {
                "id": country.id,
                "code": country.code,
                "name": country.name,
            }
            for country in countries
        ]
    }


@router.get("/countries/{country_id}")
async def get_country(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Country).where(
            Country.id == country_id
        )
    )

    country = result.scalar_one_or_none()

    if country is None:
        raise HTTPException(
            status_code=404,
            detail="Country not found",
        )

    return {
        "id": country.id,
        "code": country.code,
        "name": country.name,
    }


@router.get("/countries/{country_id}/cities")
async def get_country_cities(
    country_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(City)
        .where(City.country_id == country_id)
        .order_by(City.name.asc())
    )

    cities = result.scalars().all()

    return {
        "country_id": country_id,
        "cities": [
            {
                "id": city.id,
                "name": city.name,
                "code": city.code,
            }
            for city in cities
        ],
    }


@router.get("/cities/{city_id}")
async def get_city(
    city_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(City).where(
            City.id == city_id
        )
    )

    city = result.scalar_one_or_none()

    if city is None:
        raise HTTPException(
            status_code=404,
            detail="City not found",
        )

    return {
        "id": city.id,
        "country_id": city.country_id,
        "name": city.name,
        "code": city.code,
    }


@router.get("/cities/{city_id}/districts")
async def get_city_districts(
    city_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(District)
        .where(District.city_id == city_id)
        .order_by(District.name.asc())
    )

    districts = result.scalars().all()

    return {
        "city_id": city_id,
        "districts": [
            {
                "id": district.id,
                "name": district.name,
                "code": district.code,
            }
            for district in districts
        ],
    }


@router.get("/districts/{district_id}")
async def get_district(
    district_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(District).where(
            District.id == district_id
        )
    )

    district = result.scalar_one_or_none()

    if district is None:
        raise HTTPException(
            status_code=404,
            detail="District not found",
        )

    return {
        "id": district.id,
        "city_id": district.city_id,
        "name": district.name,
        "code": district.code,
}
