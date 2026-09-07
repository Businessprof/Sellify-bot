from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.core.exceptions import InsufficientBalanceError
from app.database.models.wallet import Wallet, WalletTransaction
from app.database.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession):
        super().__init__(Wallet, session)

    async def get_by_user_id(self, user_id: int, for_update: bool = False) -> Wallet | None:
        query = select(Wallet).where(Wallet.user_id == user_id)
        if for_update:
            # SQLite does not support FOR UPDATE, but PostgreSQL does
            if self.session.bind and self.session.bind.dialect.name == "postgresql":
                query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def credit(
        self,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str,
        reference_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Wallet, WalletTransaction]:
        """Atomically credit user balance and record ledger transaction."""
        if idempotency_key:
            existing_tx = await self.session.execute(
                select(WalletTransaction).where(WalletTransaction.idempotency_key == idempotency_key)
            )
            found = existing_tx.scalar_one_or_none()
            if found:
                wallet = await self.get_by_user_id(user_id)
                return wallet, found  # type: ignore

        wallet = await self.get_by_user_id(user_id, for_update=True)
        if not wallet:
            raise ValueError(f"Wallet for user {user_id} does not exist.")

        balance_before = wallet.balance
        wallet.balance += amount
        if tx_type == TransactionType.DEPOSIT:
            wallet.total_deposited += amount
        wallet.version += 1

        tx = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type=tx_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        self.session.add(tx)
        await self.session.flush()
        return wallet, tx

    async def debit(
        self,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str,
        reference_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Wallet, WalletTransaction]:
        """Atomically debit user balance and record ledger transaction."""
        if idempotency_key:
            existing_tx = await self.session.execute(
                select(WalletTransaction).where(WalletTransaction.idempotency_key == idempotency_key)
            )
            found = existing_tx.scalar_one_or_none()
            if found:
                wallet = await self.get_by_user_id(user_id)
                return wallet, found  # type: ignore

        wallet = await self.get_by_user_id(user_id, for_update=True)
        if not wallet:
            raise ValueError(f"Wallet for user {user_id} does not exist.")

        if wallet.balance < amount:
            raise InsufficientBalanceError(required=float(amount), current=float(wallet.balance))

        balance_before = wallet.balance
        wallet.balance -= amount
        if tx_type == TransactionType.ORDER_PAYMENT:
            wallet.total_spent += amount
        wallet.version += 1

        tx = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type=tx_type,
            amount=-amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        self.session.add(tx)
        await self.session.flush()
        return wallet, tx

    async def get_transactions(
        self, user_id: int, limit: int = 10, offset: int = 0
    ) -> list[WalletTransaction]:
        query = (
            select(WalletTransaction)
            .where(WalletTransaction.user_id == user_id)
            .order_by(WalletTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
