from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.user import User
from models.vehicle import Vehicle
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],
)


# ============================================================
# SCHEMAS
# ============================================================

class VehiclePurchase(BaseModel):
    vehicle_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    model_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    color: str = Field(
        default="default",
        max_length=50,
    )

    price: float = Field(
        ...,
        gt=0,
    )


class VehicleStateUpdate(BaseModel):
    color: str | None = Field(
        default=None,
        max_length=50,
    )

    fuel: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    health: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )


# ============================================================
# SERIALIZER
# ============================================================

def serialize_vehicle(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.id,
        "owner_id": vehicle.owner_id,

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

        "created_at": vehicle.created_at,
        "updated_at": vehicle.updated_at,
    }


# ============================================================
# MY VEHICLES
# ============================================================

@router.get("/me")
async def get_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vehicle)
        .where(
            Vehicle.owner_id == current_user.id
        )
        .order_by(
            Vehicle.created_at.asc()
        )
    )

    vehicles = result.scalars().all()

    return {
        "status": "success",
        "vehicles": [
            serialize_vehicle(vehicle)
            for vehicle in vehicles
        ],
    }


# ============================================================
# GET VEHICLE
# ============================================================

@router.get("/me/{vehicle_id}")
async def get_my_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == current_user.id,
        )
    )

    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Véhicule introuvable.",
        )

    return {
        "status": "success",
        "vehicle": serialize_vehicle(vehicle),
    }


# ============================================================
# BUY VEHICLE
# ============================================================

@router.post("/me/buy")
async def buy_vehicle(
    data: VehiclePurchase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Achat d'un véhicule avec la monnaie virtuelle du jeu.
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
            detail="Un personnage mort ne peut pas acheter de véhicule.",
        )

    price = Decimal(str(data.price))
    balance = Decimal(str(character.money))

    if balance < price:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    # --------------------------------------------------------
    # PLAQUE UNIQUE
    # --------------------------------------------------------

    license_plate = (
        f"NEXA-{current_user.id}-"
        f"{int(datetime.utcnow().timestamp())}"
    )

    # --------------------------------------------------------
    # DEBIT
    # --------------------------------------------------------

    character.money = float(
        balance - price
    )

    # --------------------------------------------------------
    # CREATION VEHICULE
    # --------------------------------------------------------

    vehicle = Vehicle(
        owner_id=current_user.id,

        vehicle_type=data.vehicle_type,
        model_id=data.model_id,
        name=data.name,

        color=data.color,
        license_plate=license_plate,

        fuel=100,
        health=100,

        # La vitesse réelle sera déterminée
        # par les données serveur du modèle.
        speed=0,

        owned=True,
        active=False,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(vehicle)

    await db.commit()
    await db.refresh(vehicle)

    return {
        "status": "success",
        "message": "Véhicule acheté.",
        "vehicle": serialize_vehicle(vehicle),
        "remaining_balance": character.money,
    }


# ============================================================
# SET ACTIVE VEHICLE
# ============================================================

@router.post("/me/{vehicle_id}/active")
async def set_active_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Définit le véhicule actuellement utilisé.

    Un joueur ne peut avoir qu'un seul véhicule actif.
    """

    result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == current_user.id,
        )
    )

    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Véhicule introuvable.",
        )

    # Désactivation des autres véhicules
    all_result = await db.execute(
        select(Vehicle).where(
            Vehicle.owner_id == current_user.id
        )
    )

    vehicles = all_result.scalars().all()

    for owned_vehicle in vehicles:
        owned_vehicle.active = False

    vehicle.active = True
    vehicle.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(vehicle)

    return {
        "status": "success",
        "message": "Véhicule sélectionné.",
        "vehicle": serialize_vehicle(vehicle),
    }


# ============================================================
# UPDATE VEHICLE STATE
# ============================================================

@router.patch("/me/{vehicle_id}")
async def update_vehicle_state(
    vehicle_id: int,
    data: VehicleStateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Met à jour l'état du véhicule.

    Les valeurs sensibles seront contrôlées par les services
    de gameplay dans la version finale.
    """

    result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == current_user.id,
        )
    )

    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Véhicule introuvable.",
        )

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in updates.items():

        if hasattr(vehicle, field):
            setattr(
                vehicle,
                field,
                value,
            )

    vehicle.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(vehicle)

    return {
        "status": "success",
        "message": "État du véhicule mis à jour.",
        "vehicle": serialize_vehicle(vehicle),
    }


# ============================================================
# DELETE / SELL VEHICLE
# ============================================================

@router.delete("/me/{vehicle_id}")
async def sell_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retire un véhicule du garage.

    Le système de revente définitif sera géré par
    l'économie du jeu.
    """

    result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == current_user.id,
        )
    )

    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Véhicule introuvable.",
        )

    if vehicle.active:
        raise HTTPException(
            status_code=400,
            detail="Impossible de vendre le véhicule actif.",
        )

    await db.delete(vehicle)
    await db.commit()

    return {
        "status": "success",
        "message": "Véhicule retiré du garage.",
        "vehicle_id": vehicle_id,
            }
