from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character


class ProgressionService:

    # XP nécessaire pour atteindre le niveau suivant.
    BASE_XP = 100
    XP_MULTIPLIER = 1.25

    @staticmethod
    def xp_required(level: int) -> int:
        if level < 1:
            level = 1

        return int(
            ProgressionService.BASE_XP
            * (ProgressionService.XP_MULTIPLIER ** (level - 1))
        )

    @staticmethod
    async def add_experience(
        db: AsyncSession,
        user_id: int,
        amount: int,
    ) -> Character | None:

        if amount <= 0:
            return None

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        character.experience += amount

        # Plusieurs niveaux peuvent être gagnés avec une seule récompense.
        while (
            character.experience
            >= ProgressionService.xp_required(character.level)
        ):
            required = ProgressionService.xp_required(
                character.level
            )

            character.experience -= required
            character.level += 1

            # Petite récompense de réputation à chaque niveau.
            character.reputation += 5

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def add_reputation(
        db: AsyncSession,
        user_id: int,
        amount: int,
    ) -> Character | None:

        if amount == 0:
            return None

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        character.reputation = max(
            0,
            character.reputation + amount,
        )

        await db.commit()
        await db.refresh(character)

        return character

    @staticmethod
    async def has_required_level(
        db: AsyncSession,
        user_id: int,
        required_level: int,
    ) -> bool:

        result = await db.execute(
            select(Character.level).where(
                Character.user_id == user_id
            )
        )

        level = result.scalar_one_or_none()

        if level is None:
            return False

        return level >= required_level

    @staticmethod
    async def get_progress(
        db: AsyncSession,
        user_id: int,
    ) -> dict | None:

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        required = ProgressionService.xp_required(
            character.level
        )

        return {
            "level": character.level,
            "experience": character.experience,
            "experience_required": required,
            "reputation": character.reputation,
            "progress_percent": round(
                (character.experience / required) * 100,
                2,
            ),
}
