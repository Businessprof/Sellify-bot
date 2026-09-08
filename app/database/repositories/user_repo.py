from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import MembershipTier, OrderStatus, UserRole
from app.core.security import generate_referral_code
from app.database.models.order import Order
from app.database.models.referral import ReferralTransaction
from app.database.models.user import User
from app.database.models.wallet import Wallet
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int, load_wallet: bool = True) -> User | None:
        query = select(User).where(User.id == telegram_id)
        if load_wallet:
            query = query.options(selectinload(User.wallet))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()

    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
        referrer_code: str | None = None,
    ) -> tuple[User, bool]:
        """
        Fetch existing user or register new user.
        If referrer_code is provided and valid, attributes referrer.
        Creates associated Wallet automatically.
        """
        user = await self.get_by_telegram_id(telegram_id, load_wallet=True)
        if user:
            # Update profile attributes if changed
            updated = False
            if user.username != username:
                user.username = username
                updated = True
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                await self.session.flush()
            return user, False

        # Attribute referrer if new user
        referred_by_id: int | None = None
        if referrer_code:
            referrer = await self.get_by_referral_code(referrer_code)
            if referrer and referrer.id != telegram_id:
                referred_by_id = referrer.id

        # Generate unique referral code
        new_code = generate_referral_code()
        while await self.get_by_referral_code(new_code):
            new_code = generate_referral_code()

        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            membership_tier=MembershipTier.BRONZE,
            role=UserRole.USER,
            referral_code=new_code,
            referred_by_id=referred_by_id,
        )
        self.session.add(user)
        await self.session.flush()

        # Create wallet
        wallet = Wallet(
            user_id=user.id,
            balance=Decimal("0.00"),
            total_deposited=Decimal("0.00"),
            total_spent=Decimal("0.00"),
        )
        self.session.add(wallet)
        await self.session.flush()

        # Reload with wallet
        user = await self.get_by_telegram_id(telegram_id, load_wallet=True)
        return user, True  # type: ignore

    async def get_referral_stats(self, user_id: int) -> tuple[int, Decimal]:
        """Returns (referral_count, total_earnings)."""
        count_q = select(func.count(User.id)).where(User.referred_by_id == user_id)
        count_res = await self.session.execute(count_q)
        count = count_res.scalar() or 0

        earnings_q = select(func.coalesce(func.sum(ReferralTransaction.commission_amount), Decimal("0.00"))).where(
            ReferralTransaction.referrer_id == user_id
        )
        earnings_res = await self.session.execute(earnings_q)
        earnings = earnings_res.scalar() or Decimal("0.00")

        return int(count), Decimal(str(earnings))

    async def get_total_spent(self, user_id: int) -> Decimal:
        """Calculate total spent on completed orders."""
        query = select(func.coalesce(func.sum(Order.total_amount), Decimal("0.00"))).where(
            Order.user_id == user_id, Order.status == OrderStatus.COMPLETED
        )
        res = await self.session.execute(query)
        val = res.scalar() or Decimal("0.00")
        return Decimal(str(val))

    async def count_all_users(self) -> int:
        """Count total registered bot users."""
        res = await self.session.execute(select(func.count(User.id)))
        return res.scalar() or 0
