from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.friend import BlockedUser, FriendRequest, Friendship
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/friends",
    tags=["Friends"],
)


# ============================================================
# SCHEMAS
# ============================================================

class FriendRequestCreate(BaseModel):
    user_id: int = Field(
        ...,
        gt=0,
    )


class FriendRequestResponse(BaseModel):
    request_id: int = Field(
        ...,
        gt=0,
    )

    accept: bool


class BlockUserRequest(BaseModel):
    user_id: int = Field(
        ...,
        gt=0,
    )


# ============================================================
# HELPERS
# ============================================================

async def get_user(
    user_id: int,
    db: AsyncSession,
):
    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Joueur introuvable.",
        )

    return user


async def is_blocked(
    user_a: int,
    user_b: int,
    db: AsyncSession,
) -> bool:

    result = await db.execute(
        select(BlockedUser).where(
            or_(
                (
                    (BlockedUser.user_id == user_a)
                    &
                    (BlockedUser.blocked_user_id == user_b)
                ),
                (
                    (BlockedUser.user_id == user_b)
                    &
                    (BlockedUser.blocked_user_id == user_a)
                ),
            )
        )
    )

    return result.scalar_one_or_none() is not None


# ============================================================
# MY FRIENDS
# ============================================================

@router.get("/me")
async def get_my_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            or_(
                Friendship.user_id == current_user.id,
                Friendship.friend_id == current_user.id,
            )
        )
    )

    friendships = result.scalars().all()

    friend_ids = []

    for friendship in friendships:

        if friendship.user_id == current_user.id:
            friend_ids.append(
                friendship.friend_id
            )
        else:
            friend_ids.append(
                friendship.user_id
            )

    if not friend_ids:
        return {
            "status": "success",
            "friends": [],
        }

    users_result = await db.execute(
        select(User).where(
            User.id.in_(friend_ids),
            User.active.is_(True),
        )
    )

    users = users_result.scalars().all()

    return {
        "status": "success",
        "friends": [
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "online": user.online,
            }
            for user in users
        ],
    }


# ============================================================
# SEND FRIEND REQUEST
# ============================================================

@router.post("/me/request")
async def send_friend_request(
    data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous ajouter vous-même.",
        )

    target_user = await get_user(
        data.user_id,
        db,
    )

    if not target_user.active:
        raise HTTPException(
            status_code=400,
            detail="Ce joueur n'est plus actif.",
        )

    if await is_blocked(
        current_user.id,
        data.user_id,
        db,
    ):
        raise HTTPException(
            status_code=403,
            detail="Cette interaction est bloquée.",
        )

    # --------------------------------------------------------
    # DEJA AMIS
    # --------------------------------------------------------

    friendship_result = await db.execute(
        select(Friendship).where(
            or_(
                (
                    (Friendship.user_id == current_user.id)
                    &
                    (Friendship.friend_id == data.user_id)
                ),
                (
                    (Friendship.user_id == data.user_id)
                    &
                    (Friendship.friend_id == current_user.id)
                ),
            )
        )
    )

    if friendship_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Vous êtes déjà amis.",
        )

    # --------------------------------------------------------
    # DEMANDE EXISTANTE
    # --------------------------------------------------------

    request_result = await db.execute(
        select(FriendRequest).where(
            or_(
                (
                    (FriendRequest.sender_id == current_user.id)
                    &
                    (FriendRequest.receiver_id == data.user_id)
                    &
                    (FriendRequest.status == "PENDING")
                ),
                (
                    (FriendRequest.sender_id == data.user_id)
                    &
                    (FriendRequest.receiver_id == current_user.id)
                    &
                    (FriendRequest.status == "PENDING")
                ),
            )
        )
    )

    existing_request = (
        request_result.scalar_one_or_none()
    )

    if existing_request:
        raise HTTPException(
            status_code=409,
            detail="Une demande d'amitié est déjà en attente.",
        )

    # --------------------------------------------------------
    # CREATION
    # --------------------------------------------------------

    friend_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=data.user_id,
        status="PENDING",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(friend_request)

    await db.commit()
    await db.refresh(friend_request)

    return {
        "status": "success",
        "message": "Demande d'amitié envoyée.",
        "request_id": friend_request.id,
    }


# ============================================================
# FRIEND REQUESTS
# ============================================================

@router.get("/me/requests")
async def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    received_result = await db.execute(
        select(FriendRequest).where(
            FriendRequest.receiver_id == current_user.id,
            FriendRequest.status == "PENDING",
        )
    )

    received = received_result.scalars().all()

    sent_result = await db.execute(
        select(FriendRequest).where(
            FriendRequest.sender_id == current_user.id,
            FriendRequest.status == "PENDING",
        )
    )

    sent = sent_result.scalars().all()

    return {
        "status": "success",

        "received": [
            {
                "id": request.id,
                "sender_id": request.sender_id,
                "receiver_id": request.receiver_id,
                "status": request.status,
                "created_at": request.created_at,
            }
            for request in received
        ],

        "sent": [
            {
                "id": request.id,
                "sender_id": request.sender_id,
                "receiver_id": request.receiver_id,
                "status": request.status,
                "created_at": request.created_at,
            }
            for request in sent
        ],
    }


# ============================================================
# RESPOND TO FRIEND REQUEST
# ============================================================

@router.post("/me/requests/respond")
async def respond_to_friend_request(
    data: FriendRequestResponse,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FriendRequest).where(
            FriendRequest.id == data.request_id,
            FriendRequest.receiver_id == current_user.id,
            FriendRequest.status == "PENDING",
        )
    )

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Demande d'amitié introuvable.",
        )

    if not data.accept:

        request.status = "REJECTED"
        request.updated_at = datetime.utcnow()

        await db.commit()

        return {
            "status": "success",
            "message": "Demande refusée.",
        }

    # --------------------------------------------------------
    # ACCEPTATION
    # --------------------------------------------------------

    if await is_blocked(
        current_user.id,
        request.sender_id,
        db,
    ):
        raise HTTPException(
            status_code=403,
            detail="Cette interaction est bloquée.",
        )

    request.status = "ACCEPTED"
    request.updated_at = datetime.utcnow()

    friendship = Friendship(
        user_id=request.sender_id,
        friend_id=current_user.id,
        created_at=datetime.utcnow(),
    )

    db.add(friendship)

    await db.commit()

    return {
        "status": "success",
        "message": "Vous êtes maintenant amis.",
        "friend_id": request.sender_id,
    }


# ============================================================
# REMOVE FRIEND
# ============================================================

@router.delete("/me/{friend_id}")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            or_(
                (
                    (Friendship.user_id == current_user.id)
                    &
                    (Friendship.friend_id == friend_id)
                ),
                (
                    (Friendship.user_id == friend_id)
                    &
                    (Friendship.friend_id == current_user.id)
                ),
            )
        )
    )

    friendship = result.scalar_one_or_none()

    if not friendship:
        raise HTTPException(
            status_code=404,
            detail="Amitié introuvable.",
        )

    await db.delete(friendship)
    await db.commit()

    return {
        "status": "success",
        "message": "Joueur retiré de vos amis.",
    }


# ============================================================
# BLOCK USER
# ============================================================

@router.post("/me/block")
async def block_user(
    data: BlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous bloquer vous-même.",
        )

    await get_user(
        data.user_id,
        db,
    )

    existing_result = await db.execute(
        select(BlockedUser).where(
            BlockedUser.user_id == current_user.id,
            BlockedUser.blocked_user_id == data.user_id,
        )
    )

    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Ce joueur est déjà bloqué.",
        )

    blocked = BlockedUser(
        user_id=current_user.id,
        blocked_user_id=data.user_id,
        created_at=datetime.utcnow(),
    )

    db.add(blocked)

    # Retirer l'amitié si elle existe
    friendship_result = await db.execute(
        select(Friendship).where(
            or_(
                (
                    (Friendship.user_id == current_user.id)
                    &
                    (Friendship.friend_id == data.user_id)
                ),
                (
                    (Friendship.user_id == data.user_id)
                    &
                    (Friendship.friend_id == current_user.id)
                ),
            )
        )
    )

    friendship = friendship_result.scalar_one_or_none()

    if friendship:
        await db.delete(friendship)

    await db.commit()

    return {
        "status": "success",
        "message": "Joueur bloqué.",
        "user_id": data.user_id,
    }


# ============================================================
# UNBLOCK USER
# ============================================================

@router.delete("/me/block/{user_id}")
async def unblock_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlockedUser).where(
            BlockedUser.user_id == current_user.id,
            BlockedUser.blocked_user_id == user_id,
        )
    )

    blocked = result.scalar_one_or_none()

    if not blocked:
        raise HTTPException(
            status_code=404,
            detail="Ce joueur n'est pas bloqué.",
        )

    await db.delete(blocked)
    await db.commit()

    return {
        "status": "success",
        "message": "Joueur débloqué.",
        "user_id": user_id,
    }


# ============================================================
# BLOCKED USERS
# ============================================================

@router.get("/me/blocked")
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlockedUser).where(
            BlockedUser.user_id == current_user.id
        )
    )

    blocked_users = result.scalars().all()

    user_ids = [
        item.blocked_user_id
        for item in blocked_users
    ]

    if not user_ids:
        return {
            "status": "success",
            "blocked_users": [],
        }

    users_result = await db.execute(
        select(User).where(
            User.id.in_(user_ids)
        )
    )

    users = users_result.scalars().all()

    return {
        "status": "success",
        "blocked_users": [
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
            }
            for user in users
        ],
}
