from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.clan import Clan, ClanMember
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/clans",
    tags=["Clans"],
)


# ============================================================
# SCHEMAS
# ============================================================

class ClanCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    emblem: str | None = Field(
        default=None,
        max_length=100,
    )


class ClanJoin(BaseModel):
    clan_id: int = Field(
        ...,
        gt=0,
    )


class ClanTreasuryRequest(BaseModel):
    amount: float = Field(
        ...,
        gt=0,
    )


class ClanReputationRequest(BaseModel):
    amount: int = Field(
        ...,
        gt=0,
    )


# ============================================================
# SERIALIZERS
# ============================================================

def serialize_clan(clan: Clan) -> dict:
    return {
        "id": clan.id,
        "name": clan.name,
        "description": clan.description,
        "emblem": clan.emblem,

        "level": clan.level,
        "reputation": clan.reputation,
        "treasury": clan.treasury,

        "created_at": clan.created_at,
        "updated_at": clan.updated_at,
    }


def serialize_member(member: ClanMember) -> dict:
    return {
        "id": member.id,
        "clan_id": member.clan_id,
        "user_id": member.user_id,
        "role": member.role,
        "joined_at": member.joined_at,
    }


# ============================================================
# GET MY CLAN
# ============================================================

@router.get("/me")
async def get_my_clan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClanMember).where(
            ClanMember.user_id == current_user.id
        )
    )

    membership = result.scalar_one_or_none()

    if not membership:
        return {
            "status": "success",
            "has_clan": False,
            "clan": None,
        }

    clan_result = await db.execute(
        select(Clan).where(
            Clan.id == membership.clan_id
        )
    )

    clan = clan_result.scalar_one_or_none()

    if not clan:
        return {
            "status": "success",
            "has_clan": False,
            "clan": None,
        }

    return {
        "status": "success",
        "has_clan": True,
        "clan": serialize_clan(clan),
        "membership": serialize_member(membership),
    }


# ============================================================
# CREATE CLAN
# ============================================================

@router.post("/me")
async def create_clan(
    data: ClanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------------
    # VERIFICATION PERSONNAGE
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

    if not character.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Un personnage mort ne peut pas créer un clan.",
        )

    # --------------------------------------------------------
    # VERIFICATION APPARTENANCE
    # --------------------------------------------------------

    membership_result = await db.execute(
        select(ClanMember).where(
            ClanMember.user_id == current_user.id
        )
    )

    existing_membership = (
        membership_result.scalar_one_or_none()
    )

    if existing_membership:
        raise HTTPException(
            status_code=409,
            detail="Vous appartenez déjà à un clan.",
        )

    # --------------------------------------------------------
    # VERIFICATION NOM
    # --------------------------------------------------------

    clan_result = await db.execute(
        select(Clan).where(
            Clan.name == data.name
        )
    )

    existing_clan = clan_result.scalar_one_or_none()

    if existing_clan:
        raise HTTPException(
            status_code=409,
            detail="Ce nom de clan est déjà utilisé.",
        )

    # --------------------------------------------------------
    # CREATION DU CLAN
    # --------------------------------------------------------

    clan = Clan(
        name=data.name,
        description=data.description,
        emblem=data.emblem,

        level=1,
        reputation=0,
        treasury=0,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(clan)

    await db.flush()

    # --------------------------------------------------------
    # CREATE OWNER MEMBER
    # --------------------------------------------------------

    member = ClanMember(
        clan_id=clan.id,
        user_id=current_user.id,
        role="LEADER",
        joined_at=datetime.utcnow(),
    )

    db.add(member)

    await db.commit()

    await db.refresh(clan)
    await db.refresh(member)

    return {
        "status": "success",
        "message": "Clan créé avec succès.",
        "clan": serialize_clan(clan),
        "membership": serialize_member(member),
    }


# ============================================================
# JOIN CLAN
# ============================================================

@router.post("/me/join")
async def join_clan(
    data: ClanJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------------
    # VERIFICATION CLAN
    # --------------------------------------------------------

    clan_result = await db.execute(
        select(Clan).where(
            Clan.id == data.clan_id
        )
    )

    clan = clan_result.scalar_one_or_none()

    if not clan:
        raise HTTPException(
            status_code=404,
            detail="Clan introuvable.",
        )

    # --------------------------------------------------------
    # DEJA MEMBRE
    # --------------------------------------------------------

    membership_result = await db.execute(
        select(ClanMember).where(
            ClanMember.user_id == current_user.id
        )
    )

    existing_membership = (
        membership_result.scalar_one_or_none()
    )

    if existing_membership:
        raise HTTPException(
            status_code=409,
            detail="Vous appartenez déjà à un clan.",
        )

    # --------------------------------------------------------
    # VERIFICATION PERSONNAGE
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

    if not character.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Un personnage mort ne peut pas rejoindre un clan.",
        )

    # --------------------------------------------------------
    # AJOUT
    # --------------------------------------------------------

    member = ClanMember(
        clan_id=clan.id,
        user_id=current_user.id,
        role="MEMBER",
        joined_at=datetime.utcnow(),
    )

    db.add(member)

    await db.commit()
    await db.refresh(member)

    return {
        "status": "success",
        "message": "Vous avez rejoint le clan.",
        "clan": serialize_clan(clan),
        "membership": serialize_member(member),
    }


# ============================================================
# LEAVE CLAN
# ============================================================

@router.post("/me/leave")
async def leave_clan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClanMember).where(
            ClanMember.user_id == current_user.id
        )
    )

    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="Vous n'appartenez à aucun clan.",
        )

    if membership.role == "LEADER":
        raise HTTPException(
            status_code=400,
            detail=(
                "Le chef doit transférer la direction "
                "avant de quitter le clan."
            ),
        )

    await db.delete(membership)

    await db.commit()

    return {
        "status": "success",
        "message": "Vous avez quitté le clan.",
    }


# ============================================================
# CLAN MEMBERS
# ============================================================

@router.get("/{clan_id}/members")
async def get_clan_members(
    clan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clan_result = await db.execute(
        select(Clan).where(
            Clan.id == clan_id
        )
    )

    clan = clan_result.scalar_one_or_none()

    if not clan:
        raise HTTPException(
            status_code=404,
            detail="Clan introuvable.",
        )

    result = await db.execute(
        select(ClanMember)
        .where(
            ClanMember.clan_id == clan_id
        )
        .order_by(
            ClanMember.joined_at.asc()
        )
    )

    members = result.scalars().all()

    return {
        "status": "success",
        "clan": serialize_clan(clan),
        "members": [
            serialize_member(member)
            for member in members
        ],
    }


# ============================================================
# CLAN TREASURY
# ============================================================

@router.post("/me/treasury/deposit")
async def deposit_clan_treasury(
    data: ClanTreasuryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dépose de la monnaie virtuelle dans la trésorerie du clan.
    """

    membership_result = await db.execute(
        select(ClanMember).where(
            ClanMember.user_id == current_user.id
        )
    )

    membership = membership_result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="Vous n'appartenez à aucun clan.",
        )

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

    amount = Decimal(str(data.amount))
    balance = Decimal(str(character.money))

    if balance < amount:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    clan_result = await db.execute(
        select(Clan).where(
            Clan.id == membership.clan_id
        )
    )

    clan = clan_result.scalar_one_or_none()

    if not clan:
        raise HTTPException(
            status_code=404,
            detail="Clan introuvable.",
        )

    character.money = float(
        balance - amount
    )

    clan.treasury = float(
        Decimal(str(clan.treasury))
        + amount
    )

    clan.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "Contribution ajoutée à la trésorerie.",

        "amount": float(amount),

        "player_balance": character.money,

        "clan_treasury": clan.treasury,
    }


# ============================================================
# CLAN REPUTATION
# ============================================================

@router.get("/{clan_id}/reputation")
async def get_clan_reputation(
    clan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Clan).where(
            Clan.id == clan_id
        )
    )

    clan = result.scalar_one_or_none()

    if not clan:
        raise HTTPException(
            status_code=404,
            detail="Clan introuvable.",
        )

    return {
        "status": "success",
        "clan_id": clan.id,
        "reputation": clan.reputation,
        "level": clan.level,
    }


# ============================================================
# CLAN PUBLIC PROFILE
# ============================================================

@router.get("/{clan_id}/public")
async def get_public_clan(
    clan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Clan).where(
            Clan.id == clan_id
        )
    )

    clan = result.scalar_one_or_none()

    if not clan:
        raise HTTPException(
            status_code=404,
            detail="Clan introuvable.",
        )

    member_result = await db.execute(
        select(ClanMember).where(
            ClanMember.clan_id == clan.id
        )
    )

    members = member_result.scalars().all()

    return {
        "status": "success",

        "clan": {
            "id": clan.id,
            "name": clan.name,
            "description": clan.description,
            "emblem": clan.emblem,

            "level": clan.level,
            "reputation": clan.reputation,

            "member_count": len(members),

            "created_at": clan.created_at,
        },
}
