from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.inventory import InventoryItem


class InventoryService:

    @staticmethod
    async def get_item(
        db: AsyncSession,
        user_id: int,
        item_id: str,
    ) -> InventoryItem | None:

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id,
                InventoryItem.item_id == item_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def add_item(
        db: AsyncSession,
        user_id: int,
        item_id: str,
        item_type: str,
        quantity: int = 1,
    ) -> InventoryItem | None:

        if quantity <= 0:
            return None

        item = await InventoryService.get_item(
            db,
            user_id,
            item_id,
        )

        if item:
            item.quantity += quantity

        else:
            item = InventoryItem(
                user_id=user_id,
                item_id=item_id,
                item_type=item_type,
                quantity=quantity,
            )

            db.add(item)

        await db.commit()
        await db.refresh(item)

        return item

    @staticmethod
    async def remove_item(
        db: AsyncSession,
        user_id: int,
        item_id: str,
        quantity: int = 1,
    ) -> bool:

        if quantity <= 0:
            return False

        item = await InventoryService.get_item(
            db,
            user_id,
            item_id,
        )

        if item is None:
            return False

        if item.quantity < quantity:
            return False

        item.quantity -= quantity

        if item.quantity == 0:
            await db.delete(item)

        await db.commit()

        return True

    @staticmethod
    async def has_item(
        db: AsyncSession,
        user_id: int,
        item_id: str,
        quantity: int = 1,
    ) -> bool:

        if quantity <= 0:
            return False

        item = await InventoryService.get_item(
            db,
            user_id,
            item_id,
        )

        if item is None:
            return False

        return item.quantity >= quantity

    @staticmethod
    async def get_inventory(
        db: AsyncSession,
        user_id: int,
    ) -> list[InventoryItem]:

        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.user_id == user_id)
            .order_by(InventoryItem.created_at.asc())
        )

        return list(result.scalars().all())
