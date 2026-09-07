from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.core.exceptions import InsufficientBalanceError
from app.database.models.user import User
from app.services.wallet_service import WalletService


@pytest.mark.asyncio
async def test_wallet_credit_and_transaction(db_session: AsyncSession, sample_user: User):
    wallet_service = WalletService(db_session)
    wallet, tx = await wallet_service.credit(
        user_id=sample_user.id,
        amount=Decimal("50.00"),
        tx_type=TransactionType.DEPOSIT,
        description="Bank deposit",
        idempotency_key="tx_dep_12345",
    )
    await db_session.commit()

    assert wallet.balance == Decimal("150.00")
    assert wallet.total_deposited == Decimal("150.00")
    assert tx.balance_before == Decimal("100.00")
    assert tx.balance_after == Decimal("150.00")
    assert tx.amount == Decimal("50.00")


@pytest.mark.asyncio
async def test_wallet_debit_success(db_session: AsyncSession, sample_user: User):
    wallet_service = WalletService(db_session)
    wallet, tx = await wallet_service.debit(
        user_id=sample_user.id,
        amount=Decimal("40.00"),
        tx_type=TransactionType.ORDER_PAYMENT,
        description="Payment for Gemini AI",
    )
    await db_session.commit()

    assert wallet.balance == Decimal("60.00")
    assert wallet.total_spent == Decimal("40.00")
    assert tx.balance_before == Decimal("100.00")
    assert tx.balance_after == Decimal("60.00")
    assert tx.amount == Decimal("-40.00")


@pytest.mark.asyncio
async def test_wallet_debit_insufficient_funds(db_session: AsyncSession, sample_user: User):
    wallet_service = WalletService(db_session)
    with pytest.raises(InsufficientBalanceError) as exc_info:
        await wallet_service.debit(
            user_id=sample_user.id,
            amount=Decimal("999.00"),
            tx_type=TransactionType.ORDER_PAYMENT,
            description="Expensive order",
        )
    assert exc_info.value.required == 999.00
    assert exc_info.value.current == 100.00


@pytest.mark.asyncio
async def test_wallet_idempotency_protection(db_session: AsyncSession, sample_user: User):
    wallet_service = WalletService(db_session)
    key = "unique_idem_key_001"

    # First credit
    w1, tx1 = await wallet_service.credit(
        user_id=sample_user.id,
        amount=Decimal("25.00"),
        idempotency_key=key,
        description="Bonus credit",
    )
    await db_session.commit()
    assert w1.balance == Decimal("125.00")

    # Second credit with same idempotency key
    w2, tx2 = await wallet_service.credit(
        user_id=sample_user.id,
        amount=Decimal("25.00"),
        idempotency_key=key,
        description="Duplicate bonus attempt",
    )
    # Balance must remain 125.00 (not 150.00)
    assert w2.balance == Decimal("125.00")
    assert tx1.id == tx2.id
