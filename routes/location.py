from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.location import PlayerLocation


router = APIRouter(
    prefix="/location",
    tags=["Location"],
)


class LocationUpdateRequest(BaseModel):
    user_id: int

    city_id: int
    district_id: int

    instance_id: str = Field(
        min_length=1,
        max_length=100,
    )

    position_x: float
    position_y: float
    position_z: float

    rotation_y: float


@router.get("/{user_id}")
async def get_player_location(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerLocation).where(
            PlayerLocation.user_id == user_id
        )
    )

    location = result.scalar_one_or_none()

    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Player location not found",
        )

    return {
        "user_id": location.user_id,
        "city_id": location.city_id,
        "district_id": location.district_id,
        "instance_id": location.instance_id,
        "position": {
            "x": location.position_x,
            "y": location.position_y,
            "z": location.position_z,
        },
        "rotation_y": location.rotation_y,
        "last_synced_at": location.last_synced_at,
    }


@router.put("/{user_id}")
async def update_player_location(
    user_id: int,
    data: LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    if data.user_id != user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID mismatch",
        )

    result = await db.execute(
        select(PlayerLocation).where(
            PlayerLocation.user_id == user_id
        )
    )

    location = result.scalar_one_or_none()

    if location is None:
        location = PlayerLocation(
            user_id=user_id,
            city_id=data.city_id,
            district_id=data.district_id,
            instance_id=data.instance_id,
            position_x=data.position_x,
            position_y=data.position_y,
            position_z=data.position_z,
            rotation_y=data.rotation_y,
            last_synced_at=datetime.utcnow(),
        )

        db.add(location)

    else:
        location.city_id = data.city_id
        location.district_id = data.district_id
        location.instance_id = data.instance_id
        location.position_x = data.position_x
        location.position_y = data.position_y
        location.position_z = data.position_z
        location.rotation_y = data.rotation_y
        location.last_synced_at = datetime.utcnow()

    await db.commit()
    await db.refresh(location)

    return {
        "status": "location_synced",
        "location": {
            "user_id": location.user_id,
            "city_id": location.city_id,
            "district_id": location.district_id,
            "instance_id": location.instance_id,
            "position": {
                "x": location.position_x,
                "y": location.position_y,
                "z": location.position_z,
            },
            "rotation_y": location.rotation_y,
            "last_synced_at": location.last_synced_at,
        },
    }


@router.get("/instance/{instance_id}/players")
async def get_instance_players(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerLocation)
        .where(
            PlayerLocation.instance_id == instance_id
        )
        .order_by(PlayerLocation.last_synced_at.desc())
    )

    players = result.scalars().all()

    return {
        "instance_id": instance_id,
        "players": [
            {
                "user_id": player.user_id,
                "city_id": player.city_id,
                "district_id": player.district_id,
                "position": {
                    "x": player.position_x,
                    "y": player.position_y,
                    "z": player.position_z,
                },
                "rotation_y": player.rotation_y,
                "last_synced_at": player.last_synced_at,
            }
            for player in players
        ],
}
