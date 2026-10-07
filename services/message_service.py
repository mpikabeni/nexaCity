from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.friend import BlockedUser
from models.message import Message


class MessageService:

    @staticmethod
    async def is_blocked(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
    ) -> bool:

        result = await db.execute(
            select(BlockedUser).where(
                BlockedUser.blocker_id == receiver_id,
                BlockedUser.blocked_id == sender_id,
            )
        )

        return result.scalar_one_or_none() is not None

    @staticmethod
    async def send_message(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
        content: str,
    ) -> Message | None:

        content = content.strip()

        if not content:
            return None

        if sender_id == receiver_id:
            return None

        if await MessageService.is_blocked(
            db,
            sender_id,
            receiver_id,
        ):
            return None

        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            is_read=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )

        db.add(message)

        await db.commit()
        await db.refresh(message)

        return message

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        user_id: int,
        other_user_id: int,
        limit: int = 50,
    ) -> list[Message]:

        limit = max(1, min(limit, 100))

        result = await db.execute(
            select(Message)
            .where(
                Message.is_deleted.is_(False),
                or_(
                    (
                        (Message.sender_id == user_id)
                        & (Message.receiver_id == other_user_id)
                    ),
                    (
                        (Message.sender_id == other_user_id)
                        & (Message.receiver_id == user_id)
                    ),
                ),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        messages = list(result.scalars().all())

        messages.reverse()

        return messages

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: int,
        message_id: int,
    ) -> Message | None:

        result = await db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.receiver_id == user_id,
                Message.is_deleted.is_(False),
            )
        )

        message = result.scalar_one_or_none()

        if message is None:
            return None

        message.is_read = True
        message.read_at = datetime.utcnow()

        await db.commit()
        await db.refresh(message)

        return message

    @staticmethod
    async def delete_message(
        db: AsyncSession,
        user_id: int,
        message_id: int,
    ) -> bool:

        result = await db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.sender_id == user_id,
                Message.is_deleted.is_(False),
            )
        )

        message = result.scalar_one_or_none()

        if message is None:
            return False

        # Suppression logique pour conserver l'historique
        # nécessaire aux contrôles et à la modération.
        message.is_deleted = True

        await db.commit()

        return True
