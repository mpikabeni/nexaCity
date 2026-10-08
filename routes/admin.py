from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.user import User
from models.character import Character
from models.session import PlayerSession
from models.economy import Transaction
from models.notification import Notification


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


ADMIN_ROLES = {
    "MODERATOR",
    "ADMIN",
    "SUPER_ADMIN",
    "OWNER",
}


class RoleUpdateRequest(BaseModel):
    admin_id: int
    user_id: int
    role: str = Field(min_length=1, max_length=30)


class PlayerStatusRequest(BaseModel):
    admin_id: int
    user_id: int
    active: bool


class AdminNotificationRequest(BaseModel):
    admin_id: int
    user_id: int
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=1000)
    notification_type: str = Field(
        default="ADMIN",
        max_length=50,
    )


async def get_admin(
    db: AsyncSession,
    admin_id: int,
):
    result = await db.execute(
        select(User).where(
            User.id == admin_id
        )
    )

    admin = result.scalar_one_or_none()

    if admin is None:
        raise HTTPException(
            status_code=404,
            detail="Administrator not found",
        )

    if admin.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Administrator permission required",
        )

    return admin


@router.get("/stats")
async def get_admin_stats(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
):
    await get_admin(db, admin_id)

    total_users = await db.scalar(
        select(func.count(User.id))
    )

    active_users = await db.scalar(
        select(func.count(User.id))
        .where(User.active == True)
    )

    online_users = await db.scalar(
        select(func.count(User.id))
        .where(User.online == True)
    )

    total_characters = await db.scalar(
        select(func.count(Character.id))
    )

    active_sessions = await db.scalar(
        select(func.count(PlayerSession.id))
        .where(PlayerSession.online == True)
    )

    return {
        "users": {
            "total": total_users or 0,
            "active": active_users or 0,
            "online": online_users or 0,
        },
        "characters": {
            "total": total_characters or 0,
        },
        "sessions": {
            "active": active_sessions or 0,
        },
    }


@router.get("/players")
async def get_players(
    admin_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    await get_admin(db, admin_id)

    limit = max(1, min(limit, 200))

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
    )

    users = result.scalars().all()

    return {
        "players": [
            {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language": user.language,
                "country": user.country,
                "role": user.role,
                "active": user.active,
                "online": user.online,
                "created_at": user.created_at,
            }
            for user in users
        ]
    }


@router.patch("/players/role")
async def update_player_role(
    data: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    admin = await get_admin(
        db,
        data.admin_id,
    )

    allowed_roles = {
        "PLAYER",
        "MODERATOR",
        "ADMIN",
        "SUPER_ADMIN",
        "OWNER",
    }

    new_role = data.role.upper()

    if new_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role",
        )

    # Seul OWNER peut créer/modifier un OWNER.
    if new_role == "OWNER" and admin.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Only OWNER can assign OWNER role",
        )

    result = await db.execute(
        select(User).where(
            User.id == data.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    # Un administrateur ne peut pas modifier
    # un OWNER sans être lui-même OWNER.
    if user.role == "OWNER" and admin.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Only OWNER can modify OWNER",
        )

    user.role = new_role

    await db.commit()
    await db.refresh(user)

    return {
        "status": "role_updated",
        "user_id": user.id,
        "role": user.role,
    }


@router.patch("/players/status")
async def update_player_status(
    data: PlayerStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    admin = await get_admin(
        db,
        data.admin_id,
    )

    result = await db.execute(
        select(User).where(
            User.id == data.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    if user.role == "OWNER" and admin.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Only OWNER can modify OWNER",
        )

    user.active = data.active

    await db.commit()

    return {
        "status": "player_status_updated",
        "user_id": user.id,
        "active": user.active,
    }


@router.post("/notifications")
async def send_admin_notification(
    data: AdminNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    await get_admin(
        db,
        data.admin_id,
    )

    result = await db.execute(
        select(User).where(
            User.id == data.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    notification = Notification(
        user_id=data.user_id,
        notification_type=data.notification_type,
        title=data.title,
        message=data.message,
        is_read=False,
    )

    db.add(notification)

    await db.commit()
    await db.refresh(notification)

    return {
        "status": "notification_sent",
        "notification_id": notification.id,
        "user_id": data.user_id,
    }


@router.get("/transactions")
async def get_transactions(
    admin_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    await get_admin(db, admin_id)

    limit = max(1, min(limit, 200))

    result = await db.execute(
        select(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    transactions = result.scalars().all()

    return {
        "transactions": [
            {
                "id": transaction.id,
                "user_id": transaction.user_id,
                "amount": transaction.amount,
                "balance_before": transaction.balance_before,
                "balance_after": transaction.balance_after,
                "type": transaction.transaction_type,
                "description": transaction.description,
                "reference": transaction.reference,
                "created_at": transaction.created_at,
            }
            for transaction in transactions
        ]
}
