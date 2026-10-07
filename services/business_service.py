from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.business import Business
from models.property import Property
from services.economy_service import EconomyService


class BusinessService:

    @staticmethod
    async def create_business(
        db: AsyncSession,
        user_id: int,
        property_id: int,
        name: str,
        business_type: str,
        city: str,
        district: str,
        capital: float,
        description: str | None = None,
    ) -> Business | None:

        if capital <= 0:
            return None

        # Vérifier que la propriété appartient bien au joueur.
        property_result = await db.execute(
            select(Property).where(
                Property.id == property_id,
                Property.owner_id == user_id,
                Property.is_owned.is_(True),
            )
        )

        property_obj = property_result.scalar_one_or_none()

        if property_obj is None:
            return None

        # Une propriété ne peut être utilisée que par une entreprise
        # active à la fois.
        existing_result = await db.execute(
            select(Business).where(
                Business.property_id == property_id,
            )
        )

        if existing_result.scalar_one_or_none():
            return None

        transaction = await EconomyService.spend_money(
            db=db,
            user_id=user_id,
            amount=capital,
            transaction_type="BUSINESS_CREATION",
            description=f"Business creation: {name}",
        )

        if transaction is None:
            return None

        business = Business(
            owner_id=user_id,
            property_id=property_id,
            name=name,
            business_type=business_type,
            description=description,
            city=city,
            district=district,
            level=1,
            reputation=0,
            capital=capital,
            revenue=0.0,
            employees_count=0,
            is_open=True,
        )

        db.add(business)

        await db.commit()
        await db.refresh(business)

        return business

    @staticmethod
    async def get_business(
        db: AsyncSession,
        user_id: int,
        business_id: int,
    ) -> Business | None:

        result = await db.execute(
            select(Business).where(
                Business.id == business_id,
                Business.owner_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_player_businesses(
        db: AsyncSession,
        user_id: int,
    ) -> list[Business]:

        result = await db.execute(
            select(Business)
            .where(Business.owner_id == user_id)
            .order_by(Business.created_at.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def upgrade_business(
        db: AsyncSession,
        user_id: int,
        business_id: int,
        price: float,
    ) -> Business | None:

        if price <= 0:
            return None

        business = await BusinessService.get_business(
            db,
            user_id,
            business_id,
        )

        if business is None:
            return None

        transaction = await EconomyService.spend_money(
            db=db,
            user_id=user_id,
            amount=price,
            transaction_type="BUSINESS_UPGRADE",
            description=f"Business upgrade: {business.name}",
        )

        if transaction is None:
            return None

        business.level += 1
        business.capital += price

        await db.commit()
        await db.refresh(business)

        return business

    @staticmethod
    async def add_revenue(
        db: AsyncSession,
        business_id: int,
        amount: float,
    ) -> Business | None:

        if amount <= 0:
            return None

        result = await db.execute(
            select(Business).where(
                Business.id == business_id,
                Business.is_open.is_(True),
            )
        )

        business = result.scalar_one_or_none()

        if business is None:
            return None

        business.revenue += amount
        business.capital += amount

        await db.commit()
        await db.refresh(business)

        return business

    @staticmethod
    async def set_open_status(
        db: AsyncSession,
        user_id: int,
        business_id: int,
        is_open: bool,
    ) -> Business | None:

        business = await BusinessService.get_business(
            db,
            user_id,
            business_id,
        )

        if business is None:
            return None

        business.is_open = is_open

        await db.commit()
        await db.refresh(business)

        return business
