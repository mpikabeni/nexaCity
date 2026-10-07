from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.property import Property
from services.economy_service import EconomyService


class PropertyService:

    @staticmethod
    async def buy_property(
        db: AsyncSession,
        user_id: int,
        property_type: str,
        name: str,
        city: str,
        district: str,
        purchase_price: float,
        address: str | None = None,
    ) -> Property | None:

        if purchase_price <= 0:
            return None

        # Empêche l'achat d'une propriété déjà possédée
        # au même emplacement.
        existing_result = await db.execute(
            select(Property).where(
                Property.owner_id == user_id,
                Property.city == city,
                Property.district == district,
                Property.name == name,
                Property.is_owned.is_(True),
            )
        )

        if existing_result.scalar_one_or_none():
            return None

        transaction = await EconomyService.spend_money(
            db=db,
            user_id=user_id,
            amount=purchase_price,
            transaction_type="PROPERTY_PURCHASE",
            description=f"Purchase: {name}",
        )

        if transaction is None:
            return None

        property_obj = Property(
            owner_id=user_id,
            property_type=property_type,
            name=name,
            city=city,
            district=district,
            address=address,
            purchase_price=purchase_price,
            current_value=purchase_price,
            level=1,
            is_owned=True,
        )

        db.add(property_obj)

        await db.commit()
        await db.refresh(property_obj)

        return property_obj

    @staticmethod
    async def get_property(
        db: AsyncSession,
        user_id: int,
        property_id: int,
    ) -> Property | None:

        result = await db.execute(
            select(Property).where(
                Property.id == property_id,
                Property.owner_id == user_id,
                Property.is_owned.is_(True),
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_player_properties(
        db: AsyncSession,
        user_id: int,
    ) -> list[Property]:

        result = await db.execute(
            select(Property)
            .where(
                Property.owner_id == user_id,
                Property.is_owned.is_(True),
            )
            .order_by(Property.created_at.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def upgrade_property(
        db: AsyncSession,
        user_id: int,
        property_id: int,
        upgrade_price: float,
        value_increase: float = 0.0,
    ) -> Property | None:

        if upgrade_price <= 0:
            return None

        property_obj = await PropertyService.get_property(
            db,
            user_id,
            property_id,
        )

        if property_obj is None:
            return None

        transaction = await EconomyService.spend_money(
            db=db,
            user_id=user_id,
            amount=upgrade_price,
            transaction_type="PROPERTY_UPGRADE",
            description=f"Upgrade: {property_obj.name}",
        )

        if transaction is None:
            return None

        property_obj.level += 1
        property_obj.current_value += max(
            0.0,
            value_increase,
        )

        await db.commit()
        await db.refresh(property_obj)

        return property_obj
