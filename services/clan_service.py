from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.clan import Clan, ClanMember


class ClanService:

    @staticmethod
    async def create_clan(
        db: AsyncSession,
        owner_id: int,
        name: str,
        tag: str,
        description: str | None = None,
    ) -> Clan | None:

        name = name.strip()
        tag = tag.strip().upper()

        if not name or not tag:
            return None

        if len(tag) > 10:
            return None

        # Vérifier que le nom n'existe pas déjà.
        name_result = await db.execute(
            select(Clan).where(Clan.name == name)
        )

        if name_result.scalar_one_or_none():
            return None

        # Vérifier que le tag n'existe pas déjà.
        tag_result = await db.execute(
            select(Clan).where(Clan.tag == tag)
        )

        if tag_result.scalar_one_or_none():
            return None

        # Un joueur ne peut être propriétaire que d'un clan.
        owner_result = await db.execute(
            select(Clan).where(Clan.owner_id == owner_id)
        )

        if owner_result.scalar_one_or_none():
            return None

        clan = Clan(
            owner_id=owner_id,
            name=name,
            tag=tag,
            description=description,
            level=1,
            reputation=0,
            treasury=0.0,
            max_members=20,
            is_public=True,
        )

        db.add(clan)

        await db.flush()

        # Le créateur devient automatiquement OWNER du clan.
        member = ClanMember(
            clan_id=clan.id,
            user_id=owner_id,
            role="OWNER",
        )

        db.add(member)

        await db.commit()
        await db.refresh(clan)

        return clan

    @staticmethod
    async def get_clan(
        db: AsyncSession,
        clan_id: int,
    ) -> Clan | None:

        result = await db.execute(
            select(Clan).where(Clan.id == clan_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_player_clan(
        db: AsyncSession,
        user_id: int,
    ) -> Clan | None:

        result = await db.execute(
            select(Clan)
            .join(
                ClanMember,
                ClanMember.clan_id == Clan.id,
            )
            .where(ClanMember.user_id == user_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def join_clan(
        db: AsyncSession,
        user_id: int,
        clan_id: int,
    ) -> ClanMember | None:

        # Vérifier que le joueur n'est pas déjà dans un clan.
        existing_result = await db.execute(
            select(ClanMember).where(
                ClanMember.user_id == user_id
            )
        )

        if existing_result.scalar_one_or_none():
            return None

        clan_result = await db.execute(
            select(Clan).where(
                Clan.id == clan_id,
                Clan.is_public.is_(True),
            )
        )

        clan = clan_result.scalar_one_or_none()

        if clan is None:
            return None

        # Vérifier la capacité maximale.
        count_result = await db.execute(
            select(func.count(ClanMember.id)).where(
                ClanMember.clan_id == clan_id
            )
        )

        member_count = count_result.scalar_one()

        if member_count >= clan.max_members:
            return None

        member = ClanMember(
            clan_id=clan_id,
            user_id=user_id,
            role="MEMBER",
        )

        db.add(member)

        await db.commit()
        await db.refresh(member)

        return member

    @staticmethod
    async def leave_clan(
        db: AsyncSession,
        user_id: int,
    ) -> bool:

        result = await db.execute(
            select(ClanMember).where(
                ClanMember.user_id == user_id
            )
        )

        member = result.scalar_one_or_none()

        if member is None:
            return False

        # Le propriétaire doit transférer son clan
        # avant de pouvoir le quitter.
        if member.role == "OWNER":
            return False

        await db.delete(member)
        await db.commit()

        return True

    @staticmethod
    async def add_treasury(
        db: AsyncSession,
        clan_id: int,
        amount: float,
    ) -> Clan | None:

        if amount <= 0:
            return None

        clan = await ClanService.get_clan(
            db,
            clan_id,
        )

        if clan is None:
            return None

        clan.treasury += amount

        await db.commit()
        await db.refresh(clan)

        return clan

    @staticmethod
    async def update_reputation(
        db: AsyncSession,
        clan_id: int,
        amount: int,
    ) -> Clan | None:

        clan = await ClanService.get_clan(
            db,
            clan_id,
        )

        if clan is None:
            return None

        clan.reputation = max(
            0,
            clan.reputation + amount,
        )

        await db.commit()
        await db.refresh(clan)

        return clan
