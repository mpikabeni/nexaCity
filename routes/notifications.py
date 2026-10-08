from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.notification import Notification


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("/{user_id}")
async def get_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )

    if unread_only:
        query = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )

    result = await db.execute(query)
    notifications = result.scalars().all()

    return {
        "user_id": user_id,
        "notifications": [
            {
                "id": notification.id,
                "type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "created_at": notification.created_at,
            }
            for notification in notifications
        ],
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )

    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.is_read = True

    await db.commit()

    return {
        "status": "notification_read",
        "notification_id": notification_id,
    }


@router.post("/{user_id}/read-all")
async def mark_all_notifications_read(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )

    notifications = result.scalars().all()

    for notification in notifications:
        notification.is_read = True

    await db.commit()

    return {
        "status": "all_notifications_read",
        "user_id": user_id,
        "updated_count": len(notifications),
}
