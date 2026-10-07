from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.election import (
    Election,
    ElectionCandidate,
    ElectionVote,
)


router = APIRouter(
    prefix="/elections",
    tags=["Elections"],
)


class CreateElectionRequest(BaseModel):
    country_id: int
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=1000)
    starts_at: datetime
    ends_at: datetime


class CandidateRequest(BaseModel):
    election_id: int
    user_id: int
    program: str = Field(default="", max_length=2000)


class VoteRequest(BaseModel):
    election_id: int
    voter_id: int
    candidate_id: int


@router.get("/")
async def get_elections(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(Election).order_by(Election.starts_at.desc())

    if active_only:
        query = query.where(Election.is_active == True)

    result = await db.execute(query)
    elections = result.scalars().all()

    return {
        "elections": [
            {
                "id": election.id,
                "country_id": election.country_id,
                "title": election.title,
                "description": election.description,
                "starts_at": election.starts_at,
                "ends_at": election.ends_at,
                "is_active": election.is_active,
            }
            for election in elections
        ]
    }


@router.get("/{election_id}")
async def get_election(
    election_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Election).where(
            Election.id == election_id
        )
    )

    election = result.scalar_one_or_none()

    if election is None:
        raise HTTPException(
            status_code=404,
            detail="Election not found",
        )

    return {
        "id": election.id,
        "country_id": election.country_id,
        "title": election.title,
        "description": election.description,
        "starts_at": election.starts_at,
        "ends_at": election.ends_at,
        "is_active": election.is_active,
    }


@router.post("/create")
async def create_election(
    data: CreateElectionRequest,
    db: AsyncSession = Depends(get_db),
):
    if data.ends_at <= data.starts_at:
        raise HTTPException(
            status_code=400,
            detail="Election end must be after start",
        )

    election = Election(
        country_id=data.country_id,
        title=data.title,
        description=data.description,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        is_active=False,
    )

    db.add(election)

    await db.commit()
    await db.refresh(election)

    return {
        "status": "election_created",
        "election": {
            "id": election.id,
            "country_id": election.country_id,
            "title": election.title,
            "starts_at": election.starts_at,
            "ends_at": election.ends_at,
            "is_active": election.is_active,
        },
    }


@router.post("/candidate")
async def add_candidate(
    data: CandidateRequest,
    db: AsyncSession = Depends(get_db),
):
    election_result = await db.execute(
        select(Election).where(
            Election.id == data.election_id
        )
    )

    election = election_result.scalar_one_or_none()

    if election is None:
        raise HTTPException(
            status_code=404,
            detail="Election not found",
        )

    if election.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot add candidates after election starts",
        )

    existing_result = await db.execute(
        select(ElectionCandidate).where(
            ElectionCandidate.election_id == data.election_id,
            ElectionCandidate.user_id == data.user_id,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Player is already a candidate",
        )

    candidate = ElectionCandidate(
        election_id=data.election_id,
        user_id=data.user_id,
        program=data.program,
        votes=0,
    )

    db.add(candidate)

    await db.commit()
    await db.refresh(candidate)

    return {
        "status": "candidate_added",
        "candidate": {
            "id": candidate.id,
            "election_id": candidate.election_id,
            "user_id": candidate.user_id,
            "program": candidate.program,
            "votes": candidate.votes,
        },
    }


@router.get("/{election_id}/candidates")
async def get_candidates(
    election_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ElectionCandidate)
        .where(
            ElectionCandidate.election_id == election_id
        )
        .order_by(ElectionCandidate.votes.desc())
    )

    candidates = result.scalars().all()

    return {
        "election_id": election_id,
        "candidates": [
            {
                "id": candidate.id,
                "user_id": candidate.user_id,
                "program": candidate.program,
                "votes": candidate.votes,
            }
            for candidate in candidates
        ],
    }


@router.post("/vote")
async def vote(
    data: VoteRequest,
    db: AsyncSession = Depends(get_db),
):
    election_result = await db.execute(
        select(Election).where(
            Election.id == data.election_id
        )
    )

    election = election_result.scalar_one_or_none()

    if election is None:
        raise HTTPException(
            status_code=404,
            detail="Election not found",
        )

    now = datetime.utcnow()

    if not election.is_active:
        raise HTTPException(
            status_code=400,
            detail="Election is not active",
        )

    if now < election.starts_at:
        raise HTTPException(
            status_code=400,
            detail="Election has not started",
        )

    if now > election.ends_at:
        raise HTTPException(
            status_code=400,
            detail="Election has ended",
        )

    candidate_result = await db.execute(
        select(ElectionCandidate).where(
            ElectionCandidate.id == data.candidate_id,
            ElectionCandidate.election_id == data.election_id,
        )
    )

    candidate = candidate_result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found",
        )

    existing_vote_result = await db.execute(
        select(ElectionVote).where(
            ElectionVote.election_id == data.election_id,
            ElectionVote.voter_id == data.voter_id,
        )
    )

    existing_vote = existing_vote_result.scalar_one_or_none()

    if existing_vote is not None:
        raise HTTPException(
            status_code=400,
            detail="Player has already voted",
        )

    vote = ElectionVote(
        election_id=data.election_id,
        voter_id=data.voter_id,
        candidate_id=data.candidate_id,
    )

    candidate.votes += 1

    db.add(vote)

    await db.commit()
    await db.refresh(vote)

    return {
        "status": "vote_recorded",
        "election_id": data.election_id,
        "candidate_id": data.candidate_id,
}
