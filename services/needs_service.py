from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character


class NeedsService:

    # Perte par heure.
    HUNGER_LOSS_PER_HOUR = 4.0
    HYDRATION_LOSS_PER_HOUR = 5.0
    ENERGY_LOSS_PER_HOUR = 3.0

    @staticmethod
    async def update_needs(
        db: AsyncSession,
        user_id: int,
    ) -> Character | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        if not character.is_alive:
            return character

        now = datetime.utcnow()
        last_update = character.updated_at or now

        elapsed_seconds = max(
            0.0,
            (now - last_update).total_seconds(),
        )

        elapsed_hours = elapsed_seconds / 3600.0

        # Évite une énorme perte si un joueur revient
        # après une très longue période hors connexion.
        elapsed_hours = min(elapsed_hours, 24.0)

        character.hunger = max(
            0.0,
            character.hunger
            - (NeedsService.HUNGER_LOSS_PER_HOUR * elapsed_hours),
        )

        character.hydration = max(
            0.0,
            character.hydration
            - (NeedsService.HYDRATION_LOSS_PER_HOUR * elapsed_hours),
        )

        character.energy = max(
            0.0,
            character.energy
            - (NeedsService.ENERGY_LOSS_PER_HOUR * elapsed_hours),
        )

        # Si la faim ou l'hydratation deviennent critiques,
        # la santé commence à diminuer.
        if character.hunger <= 10.0:
            character.health = max(
                0.0,
                character.health - (2.0 * elapsed_hours),
            )

        if character.hydration <= 10.0:
            character.health = max(
                0.0,
                character.health - (3.0 * elapsed_hours),
            )

        # Mort du personnage.
        if character.health <= 0:
            character.health = 0.0
            character.is_alive = False

        character.updated_at = now

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def eat(
        db: AsyncSession,
        user_id: int,
        hunger_restore: float = 25.0,
    ) -> Character | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return character

        character.hunger = min(
            100.0,
            character.hunger + hunger_restore,
        )

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def drink(
        db: AsyncSession,
        user_id: int,
        hydration_restore: float = 30.0,
    ) -> Character | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return character

        character.hydration = min(
            100.0,
            character.hydration + hydration_restore,
        )

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def rest(
        db: AsyncSession,
        user_id: int,
        energy_restore: float = 30.0,
    ) -> Character | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return character

        character.energy = min(
            100.0,
            character.energy + energy_restore,
        )

        await db.commit()
        await db.refresh(character)

        return character
