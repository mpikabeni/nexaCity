from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.friend import BlockedUser, Friendship
from models.message import Message
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


# ============================================================
# SCHEMAS
# ============================================================

class MessageCreate(BaseModel):
    receiver_id: int = Field(
        ...,
        gt=0,
    )

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )


class MessageReadRequest(BaseModel):
    message_id: int = Field(
        ...,
        gt=0,
    )


# ============================================================
# HELPERS
# ============================================================

async def get_user(
    user_id: int,
    db: AsyncSession,
) -> User:

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


async def are_blocked(
    user_a: int,
    user_b: int,
    db: AsyncSession,
) -> bool:

    result = await db.execute(
        select(BlockedUser).where(
            or_(
                and_(
                    BlockedUser.user_id == user_a,
                    BlockedUser.blocked_user_id == user_b,
                ),
                and_(
                    BlockedUser.user_id == user_b,
                    BlockedUser.blocked_user_id == user_a,
                ),
            )
        )
    )

    return result.scalar_one_or_none() is not None


async def are_friends(
    user_a: int,
    user_b: int,
    db: AsyncSession,
) -> bool:

    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(
                    Friendship.user_id == user_a,
                    Friendship.friend_id == user_b,
                ),
                and_(
                    Friendship.user_id == user_b,
                    Friendship.friend_id == user_a,
                ),
            )
        )
    )

    return result.scalar_one_or_none() is not None


def serialize_message(
    message: Message,
) -> dict:

    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "content": message.content,
        "is_read": message.is_read,
        "created_at": message.created_at,
    }


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/me/send")
async def send_message(
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Envoie un message privé à un autre joueur.
    """

    if data.receiver_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous envoyer un message.",
        )

    receiver = await get_user(
        data.receiver_id,
        db,
    )

    if not receiver.active:
        raise HTTPException(
            status_code=400,
            detail="Ce joueur n'est plus actif.",
        )

    # --------------------------------------------------------
    # BLOCAGE
    # --------------------------------------------------------

    if await are_blocked(
        current_user.id,
        data.receiver_id,
        db,
    ):
        raise HTTPException(
            status_code=403,
            detail="Impossible d'envoyer ce message.",
        )

    # --------------------------------------------------------
    # NETTOYAGE
    # --------------------------------------------------------

    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide.",
        )

    # --------------------------------------------------------
    # CREATION
    # --------------------------------------------------------

    message = Message(
        sender_id=current_user.id,
        receiver_id=data.receiver_id,
        content=content,
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(message)

    await db.commit()
    await db.refresh(message)

    return {
        "status": "success",
        "message": "Message envoyé.",
        "data": serialize_message(message),
    }


# ============================================================
# CONVERSATION
# ============================================================

@router.get("/me/conversation/{user_id}")
async def get_conversation(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Récupère la conversation privée entre deux joueurs.
    """

    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Utilisateur invalide.",
        )

    await get_user(
        user_id,
        db,
    )

    if await are_blocked(
        current_user.id,
        user_id,
        db,
    ):
        raise HTTPException(
            status_code=403,
            detail="Conversation inaccessible.",
        )

    result = await db.execute(
        select(Message)
        .where(
            or_(
                and_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == user_id,
                ),
                and_(
                    Message.sender_id == user_id,
                    Message.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(
            Message.created_at.asc()
        )
    )

    messages = result.scalars().all()

    # --------------------------------------------------------
    # MARQUER LES MESSAGES RECUS COMME LUS
    # --------------------------------------------------------

    unread_messages = [
        message
        for message in messages
        if (
            message.receiver_id == current_user.id
            and not message.is_read
        )
    ]

    for message in unread_messages:
        message.is_read = True

    if unread_messages:
        await db.commit()

    return {
        "status": "success",
        "user_id": user_id,
        "messages": [
            serialize_message(message)
            for message in messages
        ],
    }


# ============================================================
# MY RECEIVED MESSAGES
# ============================================================

@router.get("/me/received")
async def get_received_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les messages reçus du joueur connecté.
    """

    result = await db.execute(
        select(Message)
        .where(
            Message.receiver_id == current_user.id
        )
        .order_by(
            Message.created_at.desc()
        )
    )

    messages = result.scalars().all()

    return {
        "status": "success",
        "messages": [
            serialize_message(message)
            for message in messages
        ],
    }


# ============================================================
# MY SENT MESSAGES
# ============================================================

@router.get("/me/sent")
async def get_sent_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les messages envoyés.
    """

    result = await db.execute(
        select(Message)
        .where(
            Message.sender_id == current_user.id
        )
        .order_by(
            Message.created_at.desc()
        )
    )

    messages = result.scalars().all()

    return {
        "status": "success",
        "messages": [
            serialize_message(message)
            for message in messages
        ],
    }


# ============================================================
# MARK MESSAGE AS READ
# ============================================================

@router.post("/me/read")
async def mark_message_as_read(
    data: MessageReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(
            Message.id == data.message_id,
            Message.receiver_id == current_user.id,
        )
    )

    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message introuvable.",
        )

    message.is_read = True

    await db.commit()

    return {
        "status": "success",
        "message": "Message marqué comme lu.",
        "message_id": message.id,
    }


# ============================================================
# DELETE MESSAGE
# ============================================================

@router.delete("/me/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Supprime un message appartenant au joueur.

    Le message est supprimé côté serveur.
    """

    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id,
            ),
        )
    )

    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message introuvable.",
        )

    await db.delete(message)
    await db.commit()

    return {
        "status": "success",
        "message": "Message supprimé.",
        "message_id": message_id,
}
