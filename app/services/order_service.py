from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import OrderStatus, PaymentMethod, TransactionType
from app.core.exceptions import InsufficientBalanceError, OutOfStockError
from app.database.models.inventory import InventoryItem
from app.database.models.order import Order
from app.database.repositories.inventory_repo import InventoryRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.wallet_repo import WalletRepository
from app.services.referral_service import ReferralService


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.wallet_repo = WalletRepository(session)
        self.inventory_repo = InventoryRepository(session)
        self.product_repo = ProductRepository(session)
        self.referral_service = ReferralService(session)

    async def execute_purchase(
        self,
        user_id: int,
        variant_id: int,
        quantity: int = 1,
    ) -> tuple[Order, list[InventoryItem]]:
        """
        Executes an atomic purchase transaction:
        1. Checks and locks available stock items.
        2. Checks and debits user wallet balance.
        3. Creates Order and OrderItems.
        4. Transitions stock items to SOLD.
        5. Settles referral commissions if applicable.
        """
        variant = await self.product_repo.get_variant_by_id(variant_id)
        if not variant or not variant.is_active:
            raise ValueError("Product variant not found or inactive.")

        total_price = (variant.price * Decimal(str(quantity))).quantize(Decimal("0.01"))

        # 1. Check wallet balance first
        wallet = await self.wallet_repo.get_by_user_id(user_id)
        if not wallet or wallet.balance < total_price:
            current_bal = float(wallet.balance) if wallet else 0.0
            raise InsufficientBalanceError(required=float(total_price), current=current_bal)

        # 2. Reserve inventory items with row locking
        stock_items = await self.inventory_repo.reserve_stock(variant_id, quantity)
        if len(stock_items) < quantity:
            raise OutOfStockError(variant.name)

        delivery_lines = [item.payload for item in stock_items]
        delivery_content = "\n".join(delivery_lines)

        # 3. Create Order
        items_data = [
            {
                "product_id": variant.product_id,
                "variant_id": variant.id,
                "inventory_item_id": item.id,
                "price": variant.price,
                "quantity": 1,
            }
            for item in stock_items
        ]
        order = await self.order_repo.create_order(
            user_id=user_id,
            total_amount=total_price,
            items_data=items_data,
            payment_method=PaymentMethod.WALLET,
            currency="USD",
            delivery_content=delivery_content,
        )

        # 4. Debit wallet balance and record ledger
        desc = f"Purchase {quantity}x {variant.product.name} ({variant.name})"
        await self.wallet_repo.debit(
            user_id=user_id,
            amount=total_price,
            tx_type=TransactionType.ORDER_PAYMENT,
            description=desc,
            reference_id=str(order.id),
        )

        # 5. Mark items as SOLD
        await self.inventory_repo.complete_delivery(stock_items, order.id)

        # 6. Settle referral commission
        await self.referral_service.process_order_commission(order)

        await self.session.flush()
        return order, stock_items
