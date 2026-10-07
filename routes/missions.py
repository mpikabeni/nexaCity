from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.mission_service import MissionService


router = APIRouter(
    prefix="/missions",
    tags=["Missions"],
)


class StartMissionRequest(BaseModel):
    user_id: int
    mission_id: int


class UpdateProgressRequest(BaseModel):
    user_id: int
    player_mission_id: int
    amount: int = Field(gt=0)


class ClaimRewardRequest(BaseModel):
    user_id: int
    player_mission_id: int


@router.get("/")
async def get_available_missions(
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from models.mission import Mission

    result = await db.execute(
        select(Mission)
        .where(Mission.is_active == True)
        .order_by(Mission.id.desc())
    )

    missions = result.scalars().all()

    return {
        "missions": [
            {
                "id": mission.id,
                "title_key": mission.title_key,
                "description_key": mission.description_key,
                "mission_type": mission.mission_type,
                "required_level": mission.required_level,
                "target": mission.target,
                "reward_money": mission.reward_money,
                "reward_xp": mission.reward_xp,
                "reward_reputation": mission.reward_reputation,
                "is_active": mission.is_active,
            }
            for mission in missions
        ]
    }


@router.get("/player/{user_id}")
async def get_player_missions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from models.mission import PlayerMission

    result = await db.execute(
        select(PlayerMission)
        .where(PlayerMission.user_id == user_id)
        .order_by(PlayerMission.updated_at.desc())
    )

    missions = result.scalars().all()

    return {
        "user_id": user_id,
        "missions": [
            {
                "id": mission.id,
                "mission_id": mission.mission_id,
                "progress": mission.progress,
                "target": mission.target,
                "status": mission.status,
                "claimed": mission.claimed,
                "started_at": mission.started_at,
                "completed_at": mission.completed_at,
            }
            for mission in missions
        ],
    }


@router.post("/start")
async def start_mission(
    data: StartMissionRequest,
    db: AsyncSession = Depends(get_db),
):
    mission = await MissionService.start_mission(
        db=db,
        user_id=data.user_id,
        mission_id=data.mission_id,
    )

    if mission is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to start mission",
        )

    return {
        "status": "mission_started",
        "mission": {
            "id": mission.id,
            "mission_id": mission.mission_id,
            "progress": mission.progress,
            "target": mission.target,
            "status": mission.status,
        },
    }


@router.post("/progress")
async def update_mission_progress(
    data: UpdateProgressRequest,
    db: AsyncSession = Depends(get_db),
):
    mission = await MissionService.update_progress(
        db=db,
        user_id=data.user_id,
        player_mission_id=data.player_mission_id,
        amount=data.amount,
    )

    if mission is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to update mission progress",
        )

    return {
        "status": "progress_updated",
        "mission": {
            "id": mission.id,
            "progress": mission.progress,
            "target": mission.target,
            "status": mission.status,
            "completed_at": mission.completed_at,
        },
    }


@router.post("/claim")
async def claim_reward(
    data: ClaimRewardRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await MissionService.claim_reward(
        db=db,
        user_id=data.user_id,
        player_mission_id=data.player_mission_id,
    )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to claim mission reward",
        )

    return {
        "status": "reward_claimed",
        "mission": {
            "id": result.id,
            "status": result.status,
            "claimed": result.claimed,
        },
}
