from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character
from models.location import PlayerLocation


class PlayerSyncService:

    @staticmethod
    async def sync_location(
        db: AsyncSession,
        user_id: int,
        city_id: int | None,
        district_id: int | None,
        instance_id: str | None,
        position_x: float,
        position_y: float,
        position_z: float,
        rotation_y: float,
    ) -> PlayerLocation:

        result = await db.execute(
            select(PlayerLocation).where(
                PlayerLocation.user_id == user_id
            )
        )

        location = result.scalar_one_or_none()

        if location is None:
            location = PlayerLocation(
                user_id=user_id,
                city_id=city_id,
                district_id=district_id,
                instance_id=instance_id,
                position_x=position_x,
                position_y=position_y,
                position_z=position_z,
                rotation_y=rotation_y,
            )

            db.add(location)

        else:
            location.city_id = city_id
            location.district_id = district_id
            location.instance_id = instance_id
            location.position_x = position_x
            location.position_y = position_y
            location.position_z = position_z
            location.rotation_y = rotation_y
            location.last_synced_at = datetime.utcnow()

        await db.commit()
        await db.refresh(location)

        return location

    @staticmethod
    async def save_character_state(
        db: AsyncSession,
        user_id: int,
        energy: float,
        hunger: float,
        hydration: float,
        health: float,
    ) -> Character | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        character.energy = max(0.0, min(100.0, energy))
        character.hunger = max(0.0, min(100.0, hunger))
        character.hydration = max(0.0, min(100.0, hydration))
        character.health = max(0.0, min(100.0, health))

        if character.health <= 0:
            character.health = 0
            character.is_alive = False

        await db.commit()
        await db.refresh(character)

        return character
