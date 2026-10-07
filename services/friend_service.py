from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.friend import BlockedUser, FriendRequest, Friendship


class FriendService:

    @staticmethod
    async def are_blocked(
        db: AsyncSession,
        user_one_id: int,
        user_two_id: int,
    ) -> bool:

        result = await db.execute(
            select(BlockedUser).where(
                or_(
                    (
                        (BlockedUser.blocker_id == user_one_id)
                        & (BlockedUser.blocked_id == user_two_id)
                    ),
                    (
                        (BlockedUser.blocker_id == user_two_id)
                        & (BlockedUser.blocked_id == user_one_id)
                    ),
                )
            )
        )

        return result.scalar_one_or_none() is not None

    @staticmethod
    async def send_request(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
    ) -> FriendRequest | None:

        if sender_id == receiver_id:
            return None

        if await FriendService.are_blocked(
            db,
            sender_id,
            receiver_id,
        ):
            return None

        # Vérifier si l'amitié existe déjà.
        friendship_result = await db.execute(
            select(Friendship).where(
                or_(
                    (
                        (Friendship.user_id == sender_id)
                        & (Friendship.friend_id == receiver_id)
                    ),
                    (
                        (Friendship.user_id == receiver_id)
                        & (Friendship.friend_id == sender_id)
                    ),
                )
            )
        )

        if friendship_result.scalar_one_or_none():
            return None

        # Vérifier une demande déjà existante.
        request_result = await db.execute(
            select(FriendRequest).where(
                FriendRequest.status == "PENDING",
                or_(
                    (
                        (FriendRequest.sender_id == sender_id)
                        & (FriendRequest.receiver_id == receiver_id)
                    ),
                    (
                        (FriendRequest.sender_id == receiver_id)
                        & (FriendRequest.receiver_id == sender_id)
                    ),
                ),
            )
        )

        if request_result.scalar_one_or_none():
            return None

        request = FriendRequest(
            sender_id=sender_id,
            receiver_id=receiver_id,
            status="PENDING",
        )

        db.add(request)

        await db.commit()
        await db.refresh(request)

        return request

    @staticmethod
    async def respond_request(
        db: AsyncSession,
        user_id: int,
        request_id: int,
        accept: bool,
    ) -> Friendship | None:

        result = await db.execute(
            select(FriendRequest).where(
                FriendRequest.id == request_id,
                FriendRequest.receiver_id == user_id,
                FriendRequest.status == "PENDING",
            )
        )

        request = result.scalar_one_or_none()

        if request is None:
            return None

        request.status = "ACCEPTED" if accept else "REJECTED"
        request.responded_at = datetime.utcnow()

        if not accept:
            await db.commit()
            return None

        friendship_one = Friendship(
            user_id=request.sender_id,
            friend_id=request.receiver_id,
        )

        friendship_two = Friendship(
            user_id=request.receiver_id,
            friend_id=request.sender_id,
        )

        db.add(friendship_one)
        db.add(friendship_two)

        await db.commit()
        await db.refresh(friendship_one)

        return friendship_one

    @staticmethod
    async def remove_friend(
        db: AsyncSession,
        user_id: int,
        friend_id: int,
    ) -> bool:

        result = await db.execute(
            select(Friendship).where(
                or_(
                    (
                        (Friendship.user_id == user_id)
                        & (Friendship.friend_id == friend_id)
                    ),
                    (
                        (Friendship.user_id == friend_id)
                        & (Friendship.friend_id == user_id)
                    ),
                )
            )
        )

        friendships = result.scalars().all()

        if not friendships:
            return False

        for friendship in friendships:
            await db.delete(friendship)

        await db.commit()

        return True

    @staticmethod
    async def block_player(
        db: AsyncSession,
        blocker_id: int,
        blocked_id: int,
        reason: str | None = None,
    ) -> BlockedUser | None:

        if blocker_id == blocked_id:
            return None

        existing_result = await db.execute(
            select(BlockedUser).where(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id,
            )
        )

        if existing_result.scalar_one_or_none():
            return None

        # Supprimer l'amitié éventuelle.
        await FriendService.remove_friend(
            db,
            blocker_id,
            blocked_id,
        )

        blocked = BlockedUser(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            reason=reason,
        )

        db.add(blocked)

        await db.commit()
        await db.refresh(blocked)

        return blocked

    @staticmethod
    async def get_friends(
        db: AsyncSession,
        user_id: int,
    ) -> list[int]:

        result = await db.execute(
            select(Friendship.friend_id).where(
                Friendship.user_id == user_id
            )
        )

        return list(result.scalars().all())
