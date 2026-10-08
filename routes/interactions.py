from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.interaction import PlayerInteraction


router = APIRouter(
    prefix="/interactions",
    tags=["Interactions"],
)


class InteractionRequest(BaseModel):
    sender_id: int
    receiver_id: int
    interaction_type: str = Field(
        min_length=1,
        max_length=50,
    )
    message: str = Field(
        default="",
        max_length=500,
    )


class InteractionStatusRequest(BaseModel):
    user_id: int
    interaction_id: int
    status: str = Field(
        min_length=1,
        max_length=30,
    )


@router.post("/")
async def create_interaction(
    data: InteractionRequest,
    db: AsyncSession = Depends(get_db),
):
    if data.sender_id == data.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot interact with yourself",
        )

    interaction = PlayerInteraction(
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        interaction_type=data.interaction_type,
        message=data.message,
        status="PENDING",
    )

    db.add(interaction)

    await db.commit()
    await db.refresh(interaction)

    return {
        "status": "interaction_created",
        "interaction": {
            "id": interaction.id,
            "sender_id": interaction.sender_id,
            "receiver_id": interaction.receiver_id,
            "interaction_type": interaction.interaction_type,
            "message": interaction.message,
            "status": interaction.status,
            "created_at": interaction.created_at,
        },
    }


@router.get("/{user_id}")
async def get_player_interactions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerInteraction)
        .where(
            (
                (PlayerInteraction.sender_id == user_id)
                | (PlayerInteraction.receiver_id == user_id)
            )
        )
        .order_by(
            PlayerInteraction.created_at.desc()
        )
        .limit(100)
    )

    interactions = result.scalars().all()

    return {
        "user_id": user_id,
        "interactions": [
            {
                "id": interaction.id,
                "sender_id": interaction.sender_id,
                "receiver_id": interaction.receiver_id,
                "interaction_type": interaction.interaction_type,
                "message": interaction.message,
                "status": interaction.status,
                "created_at": interaction.created_at,
            }
            for interaction in interactions
        ],
    }


@router.patch("/{interaction_id}/status")
async def update_interaction_status(
    interaction_id: int,
    data: InteractionStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerInteraction).where(
            PlayerInteraction.id == interaction_id
        )
    )

    interaction = result.scalar_one_or_none()

    if interaction is None:
        raise HTTPException(
            status_code=404,
            detail="Interaction not found",
        )

    if data.user_id not in (
        interaction.sender_id,
        interaction.receiver_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not part of this interaction",
        )

    allowed_statuses = {
        "PENDING",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED",
    }

    if data.status.upper() not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid interaction status",
        )

    interaction.status = data.status.upper()

    await db.commit()
    await db.refresh(interaction)

    return {
        "status": "interaction_updated",
        "interaction": {
            "id": interaction.id,
            "sender_id": interaction.sender_id,
            "receiver_id": interaction.receiver_id,
            "interaction_type": interaction.interaction_type,
            "status": interaction.status,
        },
}
