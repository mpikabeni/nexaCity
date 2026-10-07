from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character


DEATH_LOCK_DURATION = timedelta(hours=4)


class DeathService:

    @staticmethod
    async def kill_player(
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

        # Empêche de réappliquer la mort à un joueur
        # qui est déjà dans sa période de blocage.
        if not character.is_alive:
            if (
                character.respawn_at
                and character.respawn_at > datetime.utcnow()
            ):
                return character

        now = datetime.utcnow()

        character.health = 0
        character.is_alive = False
        character.respawn_at = now + DEATH_LOCK_DURATION

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def can_enter_game(
        db: AsyncSession,
        user_id: int,
    ) -> bool:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return False

        if character.is_alive:
            return True

        if character.respawn_at is None:
            return True

        now = datetime.utcnow()

        if now < character.respawn_at:
            return False

        # Fin du délai de 4 heures.
        character.is_alive = True
        character.health = 100
        character.energy = 100
        character.hunger = 100
        character.hydration = 100
        character.respawn_at = None

        await db.commit()

        return True

    @staticmethod
    async def get_respawn_remaining(
        db: AsyncSession,
        user_id: int,
    ) -> int:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None or character.respawn_at is None:
            return 0

        remaining = character.respawn_at - datetime.utcnow()

        if remaining.total_seconds() <= 0:
            return 0

        return int(remaining.total_seconds())
