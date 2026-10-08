from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.demo import DemoProgress


router = APIRouter(
    prefix="/demo",
    tags=["Demo"],
)


TOTAL_STEPS = 12


class StartDemoRequest(BaseModel):
    user_id: int


class ProgressDemoRequest(BaseModel):
    user_id: int
    step: int = Field(ge=1, le=TOTAL_STEPS)
    section: str = Field(min_length=1, max_length=100)


class CompleteDemoRequest(BaseModel):
    user_id: int


async def get_demo_progress(
    db: AsyncSession,
    user_id: int,
):
    result = await db.execute(
        select(DemoProgress).where(
            DemoProgress.user_id == user_id
        )
    )

    return result.scalar_one_or_none()


@router.post("/start")
async def start_demo(
    data: StartDemoRequest,
    db: AsyncSession = Depends(get_db),
):
    demo = await get_demo_progress(
        db,
        data.user_id,
    )

    if demo is None:
        demo = DemoProgress(
            user_id=data.user_id,
            current_step=1,
            total_steps=TOTAL_STEPS,
            current_section="welcome",
            demo_started=True,
            demo_completed=False,
            skipped=False,
        )

        db.add(demo)

    else:
        if demo.demo_completed:
            return {
                "status": "already_completed",
                "demo": {
                    "current_step": demo.current_step,
                    "total_steps": demo.total_steps,
                    "current_section": demo.current_section,
                    "demo_completed": True,
                },
            }

        demo.demo_started = True
        demo.skipped = False

    await db.commit()
    await db.refresh(demo)

    return {
        "status": "demo_started",
        "demo": {
            "current_step": demo.current_step,
            "total_steps": demo.total_steps,
            "current_section": demo.current_section,
            "demo_started": demo.demo_started,
            "demo_completed": demo.demo_completed,
        },
    }


@router.get("/{user_id}")
async def get_demo(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    demo = await get_demo_progress(
        db,
        user_id,
    )

    if demo is None:
        return {
            "user_id": user_id,
            "demo_started": False,
            "demo_completed": False,
            "current_step": 0,
            "total_steps": TOTAL_STEPS,
            "current_section": None,
            "can_enter_real_game": False,
        }

    can_enter_real_game = (
        demo.demo_completed
        or demo.skipped
    )

    return {
        "user_id": user_id,
        "demo_started": demo.demo_started,
        "demo_completed": demo.demo_completed,
        "skipped": demo.skipped,
        "current_step": demo.current_step,
        "total_steps": demo.total_steps,
        "current_section": demo.current_section,
        "can_enter_real_game": can_enter_real_game,
        "started_at": demo.started_at,
        "completed_at": demo.completed_at,
    }


@router.post("/progress")
async def update_demo_progress(
    data: ProgressDemoRequest,
    db: AsyncSession = Depends(get_db),
):
    demo = await get_demo_progress(
        db,
        data.user_id,
    )

    if demo is None:
        raise HTTPException(
            status_code=404,
            detail="Demo has not been started",
        )

    if demo.demo_completed:
        return {
            "status": "already_completed",
            "current_step": demo.current_step,
            "total_steps": demo.total_steps,
        }

    if not demo.demo_started:
        raise HTTPException(
            status_code=400,
            detail="Demo has not been started",
        )

    # Empêche de revenir en arrière.
    if data.step < demo.current_step:
        raise HTTPException(
            status_code=400,
            detail="Cannot move backwards in demo",
        )

    # Empêche de sauter plusieurs étapes.
    if data.step > demo.current_step + 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot skip demo steps",
        )

    demo.current_step = data.step
    demo.current_section = data.section

    if data.step >= TOTAL_STEPS:
        demo.current_step = TOTAL_STEPS
        demo.demo_completed = True
        demo.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(demo)

    return {
        "status": (
            "demo_completed"
            if demo.demo_completed
            else "progress_updated"
        ),
        "current_step": demo.current_step,
        "total_steps": demo.total_steps,
        "current_section": demo.current_section,
        "demo_completed": demo.demo_completed,
        "can_enter_real_game": demo.demo_completed,
    }


@router.post("/complete")
async def complete_demo(
    data: CompleteDemoRequest,
    db: AsyncSession = Depends(get_db),
):
    demo = await get_demo_progress(
        db,
        data.user_id,
    )

    if demo is None:
        raise HTTPException(
            status_code=404,
            detail="Demo not found",
        )

    if demo.current_step < TOTAL_STEPS:
        raise HTTPException(
            status_code=400,
            detail="Demo is not finished",
        )

    demo.current_step = TOTAL_STEPS
    demo.demo_completed = True
    demo.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(demo)

    return {
        "status": "demo_completed",
        "user_id": data.user_id,
        "total_steps": TOTAL_STEPS,
        "can_enter_real_game": True,
        "completed_at": demo.completed_at,
    }


@router.post("/skip")
async def skip_demo(
    data: StartDemoRequest,
    db: AsyncSession = Depends(get_db),
):
    raise HTTPException(
        status_code=403,
        detail="The NEXA CITY tutorial is mandatory for new players",
)
