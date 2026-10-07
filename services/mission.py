from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character
from models.mission import Mission, PlayerMission
from services.progression_service import ProgressionService


class MissionService:

    @staticmethod
    async def start_mission(
        db: AsyncSession,
        user_id: int,
        mission_id: int,
    ) -> PlayerMission | None:

        character_result = await db.execute(
            select(Character).where(Character.user_id == user_id)
        )
        character = character_result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return None

        mission_result = await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.is_active.is_(True),
            )
        )
        mission = mission_result.scalar_one_or_none()

        if mission is None:
            return None

        if character.level < mission.required_level:
            return None

        existing_result = await db.execute(
            select(PlayerMission).where(
                PlayerMission.user_id == user_id,
                PlayerMission.mission_id == mission_id,
                PlayerMission.status.in_(["AVAILABLE", "IN_PROGRESS"]),
            )
        )

        existing = existing_result.scalar_one_or_none()

        if existing:
            return existing

        player_mission = PlayerMission(
            user_id=user_id,
            mission_id=mission_id,
            progress=0,
            target=1,
            status="IN_PROGRESS",
        )

        db.add(player_mission)

        await db.commit()
        await db.refresh(player_mission)

        return player_mission

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        user_id: int,
        player_mission_id: int,
        amount: int = 1,
    ) -> PlayerMission | None:

        if amount <= 0:
            return None

        result = await db.execute(
            select(PlayerMission).where(
                PlayerMission.id == player_mission_id,
                PlayerMission.user_id == user_id,
            )
        )

        player_mission = result.scalar_one_or_none()

        if player_mission is None:
            return None

        if player_mission.status != "IN_PROGRESS":
            return player_mission

        player_mission.progress = min(
            player_mission.target,
            player_mission.progress + amount,
        )

        if player_mission.progress >= player_mission.target:
            player_mission.status = "COMPLETED"
            player_mission.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(player_mission)

        return player_mission

    @staticmethod
    async def claim_reward(
        db: AsyncSession,
        user_id: int,
        player_mission_id: int,
    ) -> dict | None:

        result = await db.execute(
            select(PlayerMission).where(
                PlayerMission.id == player_mission_id,
                PlayerMission.user_id == user_id,
            )
        )

        player_mission = result.scalar_one_or_none()

        if player_mission is None:
            return None

        if player_mission.status != "COMPLETED":
            return None

        if player_mission.claimed_at is not None:
            return None

        mission_result = await db.execute(
            select(Mission).where(
                Mission.id == player_mission.mission_id
            )
        )

        mission = mission_result.scalar_one_or_none()

        if mission is None:
            return None

        character_result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = character_result.scalar_one_or_none()

        if character is None or not character.is_alive:
            return None

        # Récompense économique validée côté serveur.
        character.money += mission.reward_money

        player_mission.claimed_at = datetime.utcnow()
        player_mission.status = "CLAIMED"

        await db.commit()

        # XP et réputation passent également par le service
        # centralisé de progression.
        if mission.reward_experience > 0:
            await ProgressionService.add_experience(
                db,
                user_id,
                mission.reward_experience,
            )

        if mission.reward_reputation != 0:
            await ProgressionService.add_reputation(
                db,
                user_id,
                mission.reward_reputation,
            )

        await db.refresh(character)

        return {
            "mission_id": mission.id,
            "money": mission.reward_money,
            "experience": mission.reward_experience,
            "reputation": mission.reward_reputation,
            "status": "CLAIMED",
}
