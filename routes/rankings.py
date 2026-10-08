from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.ranking import PlayerRanking


router = APIRouter(
    prefix="/rankings",
    tags=["Rankings"],
)


@router.get("/global")
async def get_global_ranking(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    result = await db.execute(
        select(PlayerRanking)
        .order_by(PlayerRanking.score.desc())
        .limit(limit)
    )

    rankings = result.scalars().all()

    return {
        "type": "global",
        "rankings": [
            {
                "rank": index + 1,
                "user_id": ranking.user_id,
                "score": ranking.score,
                "level": ranking.level,
                "reputation": ranking.reputation,
                "wealth": ranking.wealth,
                "missions_completed": ranking.missions_completed,
                "events_completed": ranking.events_completed,
                "clan_activity": ranking.clan_activity,
                "achievements": ranking.achievements,
            }
            for index, ranking in enumerate(rankings)
        ],
    }


@router.get("/country/{country_id}")
async def get_country_ranking(
    country_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    result = await db.execute(
        select(PlayerRanking)
        .where(PlayerRanking.country_id == country_id)
        .order_by(PlayerRanking.score.desc())
        .limit(limit)
    )

    rankings = result.scalars().all()

    return {
        "type": "country",
        "country_id": country_id,
        "rankings": [
            {
                "rank": index + 1,
                "user_id": ranking.user_id,
                "score": ranking.score,
                "level": ranking.level,
                "reputation": ranking.reputation,
                "wealth": ranking.wealth,
                "missions_completed": ranking.missions_completed,
                "events_completed": ranking.events_completed,
                "clan_activity": ranking.clan_activity,
                "achievements": ranking.achievements,
            }
            for index, ranking in enumerate(rankings)
        ],
    }


@router.get("/city/{city_id}")
async def get_city_ranking(
    city_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    result = await db.execute(
        select(PlayerRanking)
        .where(PlayerRanking.city_id == city_id)
        .order_by(PlayerRanking.score.desc())
        .limit(limit)
    )

    rankings = result.scalars().all()

    return {
        "type": "city",
        "city_id": city_id,
        "rankings": [
            {
                "rank": index + 1,
                "user_id": ranking.user_id,
                "score": ranking.score,
                "level": ranking.level,
                "reputation": ranking.reputation,
                "wealth": ranking.wealth,
                "missions_completed": ranking.missions_completed,
                "events_completed": ranking.events_completed,
                "clan_activity": ranking.clan_activity,
                "achievements": ranking.achievements,
            }
            for index, ranking in enumerate(rankings)
        ],
    }


@router.get("/player/{user_id}")
async def get_player_ranking(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerRanking)
        .where(PlayerRanking.user_id == user_id)
    )

    ranking = result.scalar_one_or_none()

    if ranking is None:
        raise HTTPException(
            status_code=404,
            detail="Player ranking not found",
        )

    higher_result = await db.execute(
        select(PlayerRanking)
        .where(
            PlayerRanking.score > ranking.score
        )
    )

    position = len(higher_result.scalars().all()) + 1

    return {
        "user_id": user_id,
        "rank": position,
        "score": ranking.score,
        "level": ranking.level,
        "reputation": ranking.reputation,
        "wealth": ranking.wealth,
        "missions_completed": ranking.missions_completed,
        "events_completed": ranking.events_completed,
        "clan_activity": ranking.clan_activity,
        "achievements": ranking.achievements,
}
