from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.marriage import Marriage, MarriageProposal


router = APIRouter(
    prefix="/marriage",
    tags=["Marriage"],
)


class ProposalRequest(BaseModel):
    sender_id: int
    receiver_id: int
    message: str = Field(default="", max_length=500)


class ProposalResponseRequest(BaseModel):
    user_id: int
    proposal_id: int
    accept: bool


class DivorceRequest(BaseModel):
    user_id: int
    marriage_id: int


@router.get("/{user_id}")
async def get_marriage(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Marriage).where(
            (
                (Marriage.user_id_1 == user_id)
                | (Marriage.user_id_2 == user_id)
            ),
            Marriage.is_active == True,
        )
    )

    marriage = result.scalar_one_or_none()

    if marriage is None:
        return {
            "user_id": user_id,
            "married": False,
            "marriage": None,
        }

    partner_id = (
        marriage.user_id_2
        if marriage.user_id_1 == user_id
        else marriage.user_id_1
    )

    return {
        "user_id": user_id,
        "married": True,
        "marriage": {
            "id": marriage.id,
            "partner_id": partner_id,
            "user_id_1": marriage.user_id_1,
            "user_id_2": marriage.user_id_2,
            "married_at": marriage.married_at,
            "is_active": marriage.is_active,
        },
    }


@router.post("/proposal")
async def send_proposal(
    data: ProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    if data.sender_id == data.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot marry yourself",
        )

    existing_result = await db.execute(
        select(Marriage).where(
            (
                (Marriage.user_id_1 == data.sender_id)
                | (Marriage.user_id_2 == data.sender_id)
                | (Marriage.user_id_1 == data.receiver_id)
                | (Marriage.user_id_2 == data.receiver_id)
            ),
            Marriage.is_active == True,
        )
    )

    existing_marriage = existing_result.scalar_one_or_none()

    if existing_marriage is not None:
        raise HTTPException(
            status_code=400,
            detail="One of the players is already married",
        )

    pending_result = await db.execute(
        select(MarriageProposal).where(
            MarriageProposal.sender_id == data.sender_id,
            MarriageProposal.receiver_id == data.receiver_id,
            MarriageProposal.status == "PENDING",
        )
    )

    pending = pending_result.scalar_one_or_none()

    if pending is not None:
        raise HTTPException(
            status_code=400,
            detail="Proposal already sent",
        )

    proposal = MarriageProposal(
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        message=data.message,
        status="PENDING",
    )

    db.add(proposal)

    await db.commit()
    await db.refresh(proposal)

    return {
        "status": "proposal_sent",
        "proposal": {
            "id": proposal.id,
            "sender_id": proposal.sender_id,
            "receiver_id": proposal.receiver_id,
            "message": proposal.message,
            "status": proposal.status,
        },
    }


@router.post("/proposal/respond")
async def respond_to_proposal(
    data: ProposalResponseRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarriageProposal).where(
            MarriageProposal.id == data.proposal_id
        )
    )

    proposal = result.scalar_one_or_none()

    if proposal is None:
        raise HTTPException(
            status_code=404,
            detail="Marriage proposal not found",
        )

    if proposal.receiver_id != data.user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot respond to this proposal",
        )

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Proposal is no longer pending",
        )

    if not data.accept:
        proposal.status = "REJECTED"

        await db.commit()

        return {
            "status": "proposal_rejected",
            "proposal_id": proposal.id,
        }

    existing_result = await db.execute(
        select(Marriage).where(
            (
                (Marriage.user_id_1 == proposal.sender_id)
                | (Marriage.user_id_2 == proposal.sender_id)
                | (Marriage.user_id_1 == proposal.receiver_id)
                | (Marriage.user_id_2 == proposal.receiver_id)
            ),
            Marriage.is_active == True,
        )
    )

    existing_marriage = existing_result.scalar_one_or_none()

    if existing_marriage is not None:
        raise HTTPException(
            status_code=400,
            detail="One of the players is already married",
        )

    marriage = Marriage(
        user_id_1=proposal.sender_id,
        user_id_2=proposal.receiver_id,
        married_at=datetime.utcnow(),
        is_active=True,
    )

    proposal.status = "ACCEPTED"

    db.add(marriage)

    await db.commit()
    await db.refresh(marriage)

    return {
        "status": "marriage_created",
        "marriage": {
            "id": marriage.id,
            "user_id_1": marriage.user_id_1,
            "user_id_2": marriage.user_id_2,
            "married_at": marriage.married_at,
            "is_active": marriage.is_active,
        },
    }


@router.get("/proposals/{user_id}")
async def get_proposals(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarriageProposal)
        .where(
            MarriageProposal.receiver_id == user_id
        )
        .order_by(MarriageProposal.id.desc())
    )

    proposals = result.scalars().all()

    return {
        "user_id": user_id,
        "proposals": [
            {
                "id": proposal.id,
                "sender_id": proposal.sender_id,
                "receiver_id": proposal.receiver_id,
                "message": proposal.message,
                "status": proposal.status,
                "created_at": proposal.created_at,
            }
            for proposal in proposals
        ],
    }


@router.post("/divorce")
async def divorce(
    data: DivorceRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Marriage).where(
            Marriage.id == data.marriage_id,
            (
                (Marriage.user_id_1 == data.user_id)
                | (Marriage.user_id_2 == data.user_id)
            ),
            Marriage.is_active == True,
        )
    )

    marriage = result.scalar_one_or_none()

    if marriage is None:
        raise HTTPException(
            status_code=404,
            detail="Marriage not found",
        )

    marriage.is_active = False

    await db.commit()

    return {
        "status": "divorced",
        "marriage_id": marriage.id,
    }
