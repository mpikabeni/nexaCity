from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.mission import Mission, PlayerMission
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/missions",
    tags=["Missions"],
)


# ============================================================
# SCHEMAS
# ============================================================

class MissionProgressRequest(BaseModel):
    progress: int = Field(
        ...,
        gt=0,
    )


# ============================================================
# SERIALIZERS
# ============================================================

def serialize_mission(
    mission: Mission,
) -> dict:

    return {
        "id": mission.id,
        "title": mission.title,
        "description": mission.description,

        "title_key": mission.title_key,
        "description_key": mission.description_key,

        "mission_type": mission.mission_type,

        "required_level": mission.required_level,

        "reward_money": mission.reward_money,
        "reward_experience": mission.reward_experience,
        "reward_reputation": mission.reward_reputation,

        "target": mission.target,

        "active": mission.active,

        "starts_at": mission.starts_at,
        "ends_at": mission.ends_at,
    }


def serialize_player_mission(
    player_mission: PlayerMission,
) -> dict:

    return {
        "id": player_mission.id,
        "mission_id": player_mission.mission_id,

        "progress": player_mission.progress,
        "target": player_mission.target,

        "status": player_mission.status,

        "started_at": player_mission.started_at,
        "completed_at": player_mission.completed_at,
        "claimed_at": player_mission.claimed_at,
    }


# ============================================================
# GET AVAILABLE MISSIONS
# ============================================================

@router.get("/available")
async def get_available_missions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Missions disponibles pour le joueur connecté.

    Le niveau est vérifié côté serveur.
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

    result = await db.execute(
        select(Mission)
        .where(
            Mission.active.is_(True),
            Mission.required_level <= character.level,
        )
        .order_by(
            Mission.id.asc()
        )
    )

    missions = result.scalars().all()

    return {
        "status": "success",
        "missions": [
            serialize_mission(mission)
            for mission in missions
        ],
    }


# ============================================================
# GET MY MISSIONS
# ============================================================

@router.get("/me")
async def get_my_missions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerMission)
        .where(
            PlayerMission.user_id == current_user.id
        )
        .order_by(
            PlayerMission.started_at.desc()
        )
    )

    missions = result.scalars().all()

    return {
        "status": "success",
        "missions": [
            serialize_player_mission(mission)
            for mission in missions
        ],
    }


# ============================================================
# START MISSION
# ============================================================

@router.post("/{mission_id}/start")
async def start_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Commence une mission.
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
            detail="Vous ne pouvez pas commencer une mission actuellement.",
        )

    # --------------------------------------------------------
    # MISSION
    # --------------------------------------------------------

    mission_result = await db.execute(
        select(Mission).where(
            Mission.id == mission_id,
            Mission.active.is_(True),
        )
    )

    mission = mission_result.scalar_one_or_none()

    if not mission:
        raise HTTPException(
            status_code=404,
            detail="Mission introuvable ou inactive.",
        )

    # --------------------------------------------------------
    # NIVEAU
    # --------------------------------------------------------

    if character.level < mission.required_level:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Niveau {mission.required_level} requis "
                f"pour cette mission."
            ),
        )

    # --------------------------------------------------------
    # MISSION DEJA EXISTANTE
    # --------------------------------------------------------

    existing_result = await db.execute(
        select(PlayerMission).where(
            PlayerMission.user_id == current_user.id,
            PlayerMission.mission_id == mission_id,
            PlayerMission.status.in_(
                ["ACTIVE", "COMPLETED"]
            ),
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Cette mission est déjà active ou terminée.",
        )

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    target = mission.target or 1

    player_mission = PlayerMission(
        user_id=current_user.id,
        mission_id=mission.id,

        progress=0,
        target=target,

        status="ACTIVE",

        started_at=datetime.utcnow(),
        completed_at=None,
        claimed_at=None,
    )

    db.add(player_mission)

    await db.commit()
    await db.refresh(player_mission)

    return {
        "status": "success",
        "message": "Mission commencée.",
        "mission": serialize_mission(mission),
        "player_mission": serialize_player_mission(
            player_mission
        ),
    }


# ============================================================
# UPDATE MISSION PROGRESS
# ============================================================

@router.post("/{mission_id}/progress")
async def update_mission_progress(
    mission_id: int,
    data: MissionProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Met à jour la progression d'une mission.

    Dans le jeu final, la progression devra être déclenchée
    par les événements serveur plutôt que par une valeur
    librement envoyée par le frontend.
    """

    result = await db.execute(
        select(PlayerMission).where(
            PlayerMission.user_id == current_user.id,
            PlayerMission.mission_id == mission_id,
            PlayerMission.status == "ACTIVE",
        )
    )

    player_mission = result.scalar_one_or_none()

    if not player_mission:
        raise HTTPException(
            status_code=404,
            detail="Mission active introuvable.",
        )

    # --------------------------------------------------------
    # PROGRESSION
    # --------------------------------------------------------

    player_mission.progress = min(
        player_mission.progress + data.progress,
        player_mission.target,
    )

    if player_mission.progress >= player_mission.target:

        player_mission.progress = player_mission.target
        player_mission.status = "COMPLETED"
        player_mission.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(player_mission)

    return {
        "status": "success",

        "mission": serialize_player_mission(
            player_mission
        ),
    }


# ============================================================
# CLAIM REWARD
# ============================================================

@router.post("/{mission_id}/claim")
async def claim_mission_reward(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Réclame la récompense d'une mission terminée.
    """

    mission_result = await db.execute(
        select(Mission).where(
            Mission.id == mission_id
        )
    )

    mission = mission_result.scalar_one_or_none()

    if not mission:
        raise HTTPException(
            status_code=404,
            detail="Mission introuvable.",
        )

    player_result = await db.execute(
        select(PlayerMission).where(
            PlayerMission.user_id == current_user.id,
            PlayerMission.mission_id == mission_id,
            PlayerMission.status == "COMPLETED",
        )
    )

    player_mission = player_result.scalar_one_or_none()

    if not player_mission:
        raise HTTPException(
            status_code=400,
            detail="Mission non terminée ou récompense déjà récupérée.",
        )

    # --------------------------------------------------------
    # PERSONNAGE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RECOMPENSES
    # --------------------------------------------------------

    reward_money = mission.reward_money or 0
    reward_experience = mission.reward_experience or 0
    reward_reputation = mission.reward_reputation or 0

    character.money += reward_money
    character.experience += reward_experience
    character.reputation += reward_reputation

    player_mission.status = "CLAIMED"
    player_mission.claimed_at = datetime.utcnow()

    character.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",

        "message": "Récompense récupérée.",

        "rewards": {
            "money": reward_money,
            "experience": reward_experience,
            "reputation": reward_reputation,
        },

        "character": {
            "money": character.money,
            "experience": character.experience,
            "reputation": character.reputation,
            "level": character.level,
        },
    }


# ============================================================
# MISSION DETAILS
# ============================================================

@router.get("/{mission_id}")
async def get_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mission).where(
            Mission.id == mission_id
        )
    )

    mission = result.scalar_one_or_none()

    if not mission:
        raise HTTPException(
            status_code=404,
            detail="Mission introuvable.",
        )

    return {
        "status": "success",
        "mission": serialize_mission(mission),
    }
