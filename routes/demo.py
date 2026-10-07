from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.demo import DemoProgress


router = APIRouter(
    prefix="/demo",
    tags=["Demo"],
)


TOTAL_STEPS = 12


@router.post("/{user_id}/start")
async def start_demo(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DemoProgress).where(
            DemoProgress.user_id == user_id
        )
    )

    demo = result.scalar_one_or_none()

    if demo is None:
        demo = DemoProgress(
            user_id=user_id,
            current_step=0,
            total_steps=TOTAL_STEPS,
            current_section="welcome",
            demo_started=True,
            demo_completed=False,
            skipped=False,
            started_at=datetime.utcnow(),
        )

        db.add(demo)

    elif demo.demo_completed:
        return {
            "status": "already_completed",
            "demo_completed": True,
        }

    else:
        demo.demo_started = True
        demo.current_section = "welcome"

        if demo.started_at is None:
            demo.started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(demo)

    return {
        "status": "started",
        "user_id": demo.user_id,
        "current_step": demo.current_step,
        "total_steps": demo.total_steps,
        "current_section": demo.current_section,
        "demo_completed": demo.demo_completed,
    }


@router.get("/{user_id}")
async def get_demo_progress(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DemoProgress).where(
            DemoProgress.user_id == user_id
        )
    )

    demo = result.scalar_one_or_none()

    if demo is None:
        return {
            "exists": False,
            "demo_completed": False,
            "current_step": 0,
            "total_steps": TOTAL_STEPS,
        }

    return {
        "exists": True,
        "user_id": demo.user_id,
        "current_step": demo.current_step,
        "total_steps": demo.total_steps,
        "current_section": demo.current_section,
        "demo_started": demo.demo_started,
        "demo_completed": demo.demo_completed,
        "skipped": demo.skipped,
        "started_at": demo.started_at,
        "completed_at": demo.completed_at,
    }


@router.post("/{user_id}/progress")
async def update_demo_progress(
    user_id: int,
    step: int,
    section: str,
    db: AsyncSession = Depends(get_db),
):
    if step < 0 or step > TOTAL_STEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid demo step",
        )

    result = await db.execute(
        select(DemoProgress).where(
            DemoProgress.user_id == user_id
        )
    )

    demo = result.scalar_one_or_none()

    if demo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo progress not found",
        )

    if demo.demo_completed:
        return {
            "status": "already_completed",
            "demo_completed": True,
        }

    # Empêche de revenir artificiellement à une étape précédente.
    if step < demo.current_step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move backward in demo progress",
        )

    demo.current_step = step
    demo.current_section = section.strip()[:100]

    if step >= TOTAL_STEPS:
        demo.current_step = TOTAL_STEPS
        demo.demo_completed = True
        demo.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(demo)

    return {
        "status": "completed" if demo.demo_completed else "progress_updated",
        "current_step": demo.current_step,
        "total_steps": demo.total_steps,
        "current_section": demo.current_section,
        "demo_completed": demo.demo_completed,
    }


@router.post("/{user_id}/complete")
async def complete_demo(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DemoProgress).where(
            DemoProgress.user_id == user_id
        )
    )

    demo = result.scalar_one_or_none()

    if demo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo progress not found",
        )

    if demo.current_step < demo.total_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo is not finished",
        )

    demo.demo_completed = True
    demo.skipped = False
    demo.completed_at = demo.completed_at or datetime.utcnow()

    await db.commit()

    return {
        "status": "demo_completed",
        "demo_completed": True,
        "can_enter_game": True,
}
