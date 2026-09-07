from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.database.models.wallet import Wallet, WalletTransaction
from app.database.repositories.wallet_repo import WalletRepository


class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.wallet_repo = WalletRepository(session)

    async def get_wallet(self, user_id: int) -> Wallet:
        wallet = await self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise ValueError(f"Wallet for user {user_id} not found.")
        return wallet

    async def credit(
        self,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType = TransactionType.DEPOSIT,
        description: str = "Deposit funds",
        reference_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Wallet, WalletTransaction]:
        return await self.wallet_repo.credit(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            description=description,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

    async def debit(
        self,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType = TransactionType.ORDER_PAYMENT,
        description: str = "Payment for purchase",
        reference_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Wallet, WalletTransaction]:
        return await self.wallet_repo.debit(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            description=description,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

    async def get_history(self, user_id: int, limit: int = 10, offset: int = 0) -> list[WalletTransaction]:
        return await self.wallet_repo.get_transactions(user_id=user_id, limit=limit, offset=offset)
