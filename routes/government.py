from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.government import (
    Government,
    GovernmentMember,
    GovernmentDecision,
)


router = APIRouter(
    prefix="/government",
    tags=["Government"],
)


class CreateGovernmentRequest(BaseModel):
    country_id: int
    name: str = Field(min_length=1, max_length=150)
    president_id: int | None = None


class AddMemberRequest(BaseModel):
    government_id: int
    user_id: int
    position: str = Field(min_length=1, max_length=100)


class CreateDecisionRequest(BaseModel):
    government_id: int
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=1000)


@router.get("/{government_id}")
async def get_government(
    government_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Government).where(
            Government.id == government_id
        )
    )

    government = result.scalar_one_or_none()

    if government is None:
        raise HTTPException(
            status_code=404,
            detail="Government not found",
        )

    return {
        "id": government.id,
        "country_id": government.country_id,
        "name": government.name,
        "president_id": government.president_id,
        "created_at": government.created_at,
    }


@router.post("/create")
async def create_government(
    data: CreateGovernmentRequest,
    db: AsyncSession = Depends(get_db),
):
    government = Government(
        country_id=data.country_id,
        name=data.name,
        president_id=data.president_id,
    )

    db.add(government)

    await db.commit()
    await db.refresh(government)

    return {
        "status": "government_created",
        "government": {
            "id": government.id,
            "country_id": government.country_id,
            "name": government.name,
            "president_id": government.president_id,
        },
    }


@router.post("/members")
async def add_government_member(
    data: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
):
    government_result = await db.execute(
        select(Government).where(
            Government.id == data.government_id
        )
    )

    government = government_result.scalar_one_or_none()

    if government is None:
        raise HTTPException(
            status_code=404,
            detail="Government not found",
        )

    member = GovernmentMember(
        government_id=data.government_id,
        user_id=data.user_id,
        position=data.position,
    )

    db.add(member)

    await db.commit()
    await db.refresh(member)

    return {
        "status": "government_member_added",
        "member": {
            "id": member.id,
            "government_id": member.government_id,
            "user_id": member.user_id,
            "position": member.position,
        },
    }


@router.get("/{government_id}/members")
async def get_government_members(
    government_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GovernmentMember)
        .where(
            GovernmentMember.government_id == government_id
        )
        .order_by(GovernmentMember.id.asc())
    )

    members = result.scalars().all()

    return {
        "government_id": government_id,
        "members": [
            {
                "id": member.id,
                "user_id": member.user_id,
                "position": member.position,
            }
            for member in members
        ],
    }


@router.post("/decisions")
async def create_decision(
    data: CreateDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    government_result = await db.execute(
        select(Government).where(
            Government.id == data.government_id
        )
    )

    government = government_result.scalar_one_or_none()

    if government is None:
        raise HTTPException(
            status_code=404,
            detail="Government not found",
        )

    decision = GovernmentDecision(
        government_id=data.government_id,
        title=data.title,
        description=data.description,
        status="PENDING",
    )

    db.add(decision)

    await db.commit()
    await db.refresh(decision)

    return {
        "status": "decision_created",
        "decision": {
            "id": decision.id,
            "government_id": decision.government_id,
            "title": decision.title,
            "description": decision.description,
            "status": decision.status,
        },
    }


@router.get("/{government_id}/decisions")
async def get_decisions(
    government_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GovernmentDecision)
        .where(
            GovernmentDecision.government_id == government_id
        )
        .order_by(GovernmentDecision.id.desc())
    )

    decisions = result.scalars().all()

    return {
        "government_id": government_id,
        "decisions": [
            {
                "id": decision.id,
                "title": decision.title,
                "description": decision.description,
                "status": decision.status,
                "created_at": decision.created_at,
            }
            for decision in decisions
        ],
}
