from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character
from models.vehicle import Vehicle
from services.economy_service import EconomyService


class VehicleService:

    @staticmethod
    async def buy_vehicle(
        db: AsyncSession,
        user_id: int,
        vehicle_type: str,
        model_id: str,
        name: str,
        price: float,
        color: str | None = None,
    ) -> Vehicle | None:

        if price <= 0:
            return None

        character_result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = character_result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return None

        # Le prix est vérifié côté serveur.
        transaction = await EconomyService.spend_money(
            db=db,
            user_id=user_id,
            amount=price,
            transaction_type="VEHICLE_PURCHASE",
            description=f"Purchase: {name}",
        )

        if transaction is None:
            return None

        vehicle = Vehicle(
            owner_id=user_id,
            vehicle_type=vehicle_type,
            model_id=model_id,
            name=name,
            color=color,
            license_plate=f"NEXA-{uuid4().hex[:8].upper()}",
            fuel=100.0,
            health=100.0,
            speed=0.0,
            is_owned=True,
            is_active=False,
        )

        db.add(vehicle)

        await db.commit()
        await db.refresh(vehicle)

        return vehicle

    @staticmethod
    async def get_vehicle(
        db: AsyncSession,
        user_id: int,
        vehicle_id: int,
    ) -> Vehicle | None:

        result = await db.execute(
            select(Vehicle).where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_id == user_id,
                Vehicle.is_owned.is_(True),
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_player_vehicles(
        db: AsyncSession,
        user_id: int,
    ) -> list[Vehicle]:

        result = await db.execute(
            select(Vehicle)
            .where(
                Vehicle.owner_id == user_id,
                Vehicle.is_owned.is_(True),
            )
            .order_by(Vehicle.purchased_at.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def set_active_vehicle(
        db: AsyncSession,
        user_id: int,
        vehicle_id: int,
    ) -> Vehicle | None:

        vehicle = await VehicleService.get_vehicle(
            db,
            user_id,
            vehicle_id,
        )

        if vehicle is None:
            return None

        # Un seul véhicule actif par joueur.
        result = await db.execute(
            select(Vehicle).where(
                Vehicle.owner_id == user_id,
                Vehicle.is_active.is_(True),
            )
        )

        active_vehicles = result.scalars().all()

        for active_vehicle in active_vehicles:
            active_vehicle.is_active = False

        vehicle.is_active = True

        await db.commit()
        await db.refresh(vehicle)

        return vehicle

    @staticmethod
    async def update_vehicle_state(
        db: AsyncSession,
        user_id: int,
        vehicle_id: int,
        fuel: float | None = None,
        health: float | None = None,
        speed: float | None = None,
    ) -> Vehicle | None:

        vehicle = await VehicleService.get_vehicle(
            db,
            user_id,
            vehicle_id,
        )

        if vehicle is None:
            return None

        if fuel is not None:
            vehicle.fuel = max(0.0, min(100.0, fuel))

        if health is not None:
            vehicle.health = max(0.0, min(100.0, health))

        if speed is not None:
            vehicle.speed = max(0.0, speed)

        await db.commit()
        await db.refresh(vehicle)

        return vehicle
