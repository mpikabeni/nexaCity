from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character
from models.economy import Transaction


class EconomyService:

    @staticmethod
    async def get_balance(
        db: AsyncSession,
        user_id: int,
    ) -> float | None:

        result = await db.execute(
            select(Character.money).where(
                Character.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def add_money(
        db: AsyncSession,
        user_id: int,
        amount: float,
        transaction_type: str,
        description: str | None = None,
    ) -> Transaction | None:

        if amount <= 0:
            return None

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        balance_before = character.money
        character.money += amount
        balance_after = character.money

        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            transaction_type=transaction_type,
            description=description,
            reference=f"NEXA-{uuid4().hex}",
            created_at=datetime.utcnow(),
        )

        db.add(transaction)

        await db.commit()
        await db.refresh(transaction)

        return transaction

    @staticmethod
    async def spend_money(
        db: AsyncSession,
        user_id: int,
        amount: float,
        transaction_type: str,
        description: str | None = None,
    ) -> Transaction | None:

        if amount <= 0:
            return None

        result = await db.execute(
            select(Character).where(
                Character.user_id == user_id
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            return None

        if character.money < amount:
            return None

        balance_before = character.money
        character.money -= amount
        balance_after = character.money

        transaction = Transaction(
            user_id=user_id,
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            transaction_type=transaction_type,
            description=description,
            reference=f"NEXA-{uuid4().hex}",
            created_at=datetime.utcnow(),
        )

        db.add(transaction)

        await db.commit()
        await db.refresh(transaction)

        return transaction

    @staticmethod
    async def transfer_money(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
        amount: float,
    ) -> bool:

        if amount <= 0:
            return False

        if sender_id == receiver_id:
            return False

        sender_result = await db.execute(
            select(Character).where(
                Character.user_id == sender_id
            )
        )

        sender = sender_result.scalar_one_or_none()

        receiver_result = await db.execute(
            select(Character).where(
                Character.user_id == receiver_id
            )
        )

        receiver = receiver_result.scalar_one_or_none()

        if sender is None or receiver is None:
            return False

        if not sender.is_alive or not receiver.is_alive:
            return False

        if sender.money < amount:
            return False

        sender_before = sender.money
        receiver_before = receiver.money

        sender.money -= amount
        receiver.money += amount

        sender_transaction = Transaction(
            user_id=sender_id,
            amount=-amount,
            balance_before=sender_before,
            balance_after=sender.money,
            transaction_type="TRANSFER_SENT",
            description=f"Transfer to player {receiver_id}",
            reference=f"NEXA-{uuid4().hex}",
            created_at=datetime.utcnow(),
        )

        receiver_transaction = Transaction(
            user_id=receiver_id,
            amount=amount,
            balance_before=receiver_before,
            balance_after=receiver.money,
            transaction_type="TRANSFER_RECEIVED",
            description=f"Transfer from player {sender_id}",
            reference=f"NEXA-{uuid4().hex}",
            created_at=datetime.utcnow(),
        )

        db.add(sender_transaction)
        db.add(receiver_transaction)

        await db.commit()

        return True
