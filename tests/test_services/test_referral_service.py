from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MembershipTier, OrderStatus, UserRole
from app.database.models.order import Order
from app.database.models.user import User
from app.database.models.wallet import Wallet
from app.services.referral_service import ReferralService


@pytest.mark.asyncio
async def test_referral_commission_payout(db_session: AsyncSession):
    # Create Referrer (User A)
    user_a = User(
        id=1001,
        first_name="User A",
        referral_code="REFUSERA",
        membership_tier=MembershipTier.BRONZE,
        role=UserRole.USER,
    )
    db_session.add(user_a)
    await db_session.flush()

    wallet_a = Wallet(user_id=user_a.id, balance=Decimal("0.00"), total_deposited=Decimal("0.00"), total_spent=Decimal("0.00"))
    db_session.add(wallet_a)
    await db_session.flush()

    # Create Referee (User B) referred by User A
    user_b = User(
        id=1002,
        first_name="User B",
        referral_code="REFUSERB",
        referred_by_id=user_a.id,
        membership_tier=MembershipTier.BRONZE,
        role=UserRole.USER,
    )
    db_session.add(user_b)
    await db_session.flush()

    wallet_b = Wallet(user_id=user_b.id, balance=Decimal("200.00"), total_deposited=Decimal("200.00"), total_spent=Decimal("0.00"))
    db_session.add(wallet_b)
    await db_session.flush()

    # User B makes an order of $100.00
    order = Order(
        order_number="ORD-TEST-001",
        user_id=user_b.id,
        total_amount=Decimal("100.00"),
        status=OrderStatus.COMPLETED,
    )
    db_session.add(order)
    await db_session.commit()

    # Process referral commission (10% default = $10.00)
    referral_service = ReferralService(db_session)
    commission = await referral_service.process_order_commission(order)
    await db_session.commit()

    assert commission == Decimal("10.00")
    await db_session.refresh(wallet_a)
    assert wallet_a.balance == Decimal("10.00")
