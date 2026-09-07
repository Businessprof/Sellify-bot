from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import TransactionType
from app.database.models.order import Order
from app.database.models.referral import Referral, ReferralTransaction
from app.database.models.user import User
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.wallet_repo import WalletRepository


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.wallet_repo = WalletRepository(session)

    def generate_referral_link(self, referral_code: str) -> str:
        return f"https://t.me/{settings.BOT_USERNAME}?start=ref_{referral_code}"

    async def get_referral_stats(self, user_id: int) -> tuple[int, Decimal]:
        return await self.user_repo.get_referral_stats(user_id)

    async def process_order_commission(self, order: Order) -> Decimal:
        """
        Calculates and credits referral commission if the purchaser was referred.
        """
        user = await self.user_repo.get_by_telegram_id(order.user_id, load_wallet=False)
        if not user or not user.referred_by_id:
            return Decimal("0.00")

        referrer_id = user.referred_by_id

        # Get referral configuration
        ref_record = await self.session.execute(
            select(Referral).where(
                Referral.referrer_id == referrer_id,
                Referral.referee_id == user.id,
            )
        )
        referral = ref_record.scalar_one_or_none()
        rate = referral.commission_rate if referral else Decimal(str(settings.DEFAULT_REFERRAL_COMMISSION_PERCENT))

        commission = (order.total_amount * (rate / Decimal("100.00"))).quantize(Decimal("0.01"))
        if commission <= Decimal("0.00"):
            return Decimal("0.00")

        # Credit referrer's wallet
        desc = f"Referral commission from order {order.order_number}"
        await self.wallet_repo.credit(
            user_id=referrer_id,
            amount=commission,
            tx_type=TransactionType.REFERRAL_BONUS,
            description=desc,
            reference_id=str(order.id),
        )

        # Record referral transaction
        ref_tx = ReferralTransaction(
            referrer_id=referrer_id,
            referee_id=user.id,
            order_id=order.id,
            order_amount=order.total_amount,
            commission_amount=commission,
            status="PAID",
        )
        self.session.add(ref_tx)

        if referral:
            referral.total_commission_earned += commission

        await self.session.flush()
        return commission
