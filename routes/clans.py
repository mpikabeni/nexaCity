from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.clan_service import ClanService


router = APIRouter(
    prefix="/clans",
    tags=["Clans"],
)


class CreateClanRequest(BaseModel):
    user_id: int
    name: str = Field(min_length=3, max_length=100)
    tag: str = Field(min_length=2, max_length=10)
    description: str = Field(default="", max_length=500)
    emblem: str = Field(default="default", max_length=100)
    max_members: int = Field(default=50, ge=2, le=1000)
    is_public: bool = True


class JoinClanRequest(BaseModel):
    user_id: int
    clan_id: int


class LeaveClanRequest(BaseModel):
    user_id: int
    clan_id: int


class TreasuryRequest(BaseModel):
    user_id: int
    clan_id: int
    amount: float = Field(gt=0)


class ReputationRequest(BaseModel):
    clan_id: int
    amount: int


@router.get("/{clan_id}")
async def get_clan(
    clan_id: int,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.get_clan(db, clan_id)

    if clan is None:
        raise HTTPException(
            status_code=404,
            detail="Clan not found",
        )

    return {
        "id": clan.id,
        "name": clan.name,
        "tag": clan.tag,
        "description": clan.description,
        "emblem": clan.emblem,
        "owner_id": clan.owner_id,
        "max_members": clan.max_members,
        "is_public": clan.is_public,
        "treasury": clan.treasury,
        "reputation": clan.reputation,
        "created_at": clan.created_at,
    }


@router.get("/player/{user_id}")
async def get_player_clan(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.get_player_clan(
        db,
        user_id,
    )

    if clan is None:
        return {
            "user_id": user_id,
            "clan": None,
        }

    return {
        "user_id": user_id,
        "clan": {
            "id": clan.id,
            "name": clan.name,
            "tag": clan.tag,
            "description": clan.description,
            "emblem": clan.emblem,
            "owner_id": clan.owner_id,
            "max_members": clan.max_members,
            "is_public": clan.is_public,
            "treasury": clan.treasury,
            "reputation": clan.reputation,
        },
    }


@router.post("/create")
async def create_clan(
    data: CreateClanRequest,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.create_clan(
        db=db,
        owner_id=data.user_id,
        name=data.name,
        tag=data.tag,
        description=data.description,
        emblem=data.emblem,
        max_members=data.max_members,
        is_public=data.is_public,
    )

    if clan is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to create clan",
        )

    return {
        "status": "clan_created",
        "clan": {
            "id": clan.id,
            "name": clan.name,
            "tag": clan.tag,
            "owner_id": clan.owner_id,
            "max_members": clan.max_members,
            "is_public": clan.is_public,
        },
    }


@router.post("/join")
async def join_clan(
    data: JoinClanRequest,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.join_clan(
        db=db,
        user_id=data.user_id,
        clan_id=data.clan_id,
    )

    if clan is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to join clan",
        )

    return {
        "status": "joined_clan",
        "clan_id": clan.id,
        "clan_name": clan.name,
    }


@router.post("/leave")
async def leave_clan(
    data: LeaveClanRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await ClanService.leave_clan(
        db=db,
        user_id=data.user_id,
        clan_id=data.clan_id,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Unable to leave clan",
        )

    return {
        "status": "left_clan",
        "clan_id": data.clan_id,
    }


@router.post("/treasury")
async def add_treasury(
    data: TreasuryRequest,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.add_treasury(
        db=db,
        user_id=data.user_id,
        clan_id=data.clan_id,
        amount=data.amount,
    )

    if clan is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to add money to clan treasury",
        )

    return {
        "status": "treasury_updated",
        "clan_id": clan.id,
        "treasury": clan.treasury,
    }


@router.patch("/reputation")
async def update_reputation(
    data: ReputationRequest,
    db: AsyncSession = Depends(get_db),
):
    clan = await ClanService.update_reputation(
        db=db,
        clan_id=data.clan_id,
        amount=data.amount,
    )

    if clan is None:
        raise HTTPException(
            status_code=404,
            detail="Clan not found",
        )

    return {
        "status": "reputation_updated",
        "clan_id": clan.id,
        "reputation": clan.reputation,
}
