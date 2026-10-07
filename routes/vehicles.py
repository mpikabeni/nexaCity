from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.vehicle_service import VehicleService


router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],
)


class BuyVehicleRequest(BaseModel):
    user_id: int
    vehicle_type: str = Field(min_length=1, max_length=50)
    model_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="default", max_length=50)
    price: float = Field(gt=0)


class ActiveVehicleRequest(BaseModel):
    user_id: int
    vehicle_id: int


class VehicleStateRequest(BaseModel):
    fuel: float = Field(ge=0, le=100)
    health: float = Field(ge=0, le=100)
    speed: float = Field(ge=0)


@router.get("/{user_id}")
async def get_player_vehicles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    vehicles = await VehicleService.get_player_vehicles(
        db,
        user_id,
    )

    return {
        "user_id": user_id,
        "vehicles": [
            {
                "id": vehicle.id,
                "vehicle_type": vehicle.vehicle_type,
                "model_id": vehicle.model_id,
                "name": vehicle.name,
                "color": vehicle.color,
                "license_plate": vehicle.license_plate,
                "fuel": vehicle.fuel,
                "health": vehicle.health,
                "speed": vehicle.speed,
                "owned": vehicle.owned,
                "active": vehicle.active,
            }
            for vehicle in vehicles
        ],
    }


@router.get("/{user_id}/{vehicle_id}")
async def get_vehicle(
    user_id: int,
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await VehicleService.get_vehicle(
        db,
        user_id,
        vehicle_id,
    )

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    return {
        "id": vehicle.id,
        "vehicle_type": vehicle.vehicle_type,
        "model_id": vehicle.model_id,
        "name": vehicle.name,
        "color": vehicle.color,
        "license_plate": vehicle.license_plate,
        "fuel": vehicle.fuel,
        "health": vehicle.health,
        "speed": vehicle.speed,
        "owned": vehicle.owned,
        "active": vehicle.active,
    }


@router.post("/buy")
async def buy_vehicle(
    data: BuyVehicleRequest,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await VehicleService.buy_vehicle(
        db=db,
        user_id=data.user_id,
        vehicle_type=data.vehicle_type,
        model_id=data.model_id,
        name=data.name,
        color=data.color,
        price=data.price,
    )

    if vehicle is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to purchase vehicle",
        )

    return {
        "status": "vehicle_purchased",
        "vehicle": {
            "id": vehicle.id,
            "vehicle_type": vehicle.vehicle_type,
            "model_id": vehicle.model_id,
            "name": vehicle.name,
            "color": vehicle.color,
            "license_plate": vehicle.license_plate,
            "fuel": vehicle.fuel,
            "health": vehicle.health,
            "speed": vehicle.speed,
            "active": vehicle.active,
        },
    }


@router.post("/active")
async def set_active_vehicle(
    data: ActiveVehicleRequest,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await VehicleService.set_active_vehicle(
        db=db,
        user_id=data.user_id,
        vehicle_id=data.vehicle_id,
    )

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found or not owned by player",
        )

    return {
        "status": "vehicle_activated",
        "vehicle_id": vehicle.id,
    }


@router.patch("/{vehicle_id}/state")
async def update_vehicle_state(
    vehicle_id: int,
    data: VehicleStateRequest,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await VehicleService.update_vehicle_state(
        db=db,
        vehicle_id=vehicle_id,
        fuel=data.fuel,
        health=data.health,
        speed=data.speed,
    )

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    return {
        "status": "vehicle_updated",
        "vehicle": {
            "id": vehicle.id,
            "fuel": vehicle.fuel,
            "health": vehicle.health,
            "speed": vehicle.speed,
        },
}
