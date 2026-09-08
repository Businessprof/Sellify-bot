import secrets
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import OrderStatus, PaymentMethod
from app.database.models.order import Order, OrderItem
from app.database.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def create_order(
        self,
        user_id: int,
        total_amount: Decimal,
        items_data: list[dict],
        payment_method: PaymentMethod = PaymentMethod.WALLET,
        currency: str = "USD",
        delivery_content: str | None = None,
    ) -> Order:
        order_num = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
        order = Order(
            order_number=order_num,
            user_id=user_id,
            status=OrderStatus.COMPLETED,
            total_amount=total_amount,
            currency=currency,
            payment_method=payment_method,
            delivery_content=delivery_content,
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(order)
        await self.session.flush()

        for item in items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                variant_id=item["variant_id"],
                inventory_item_id=item.get("inventory_item_id"),
                price=item["price"],
                quantity=item.get("quantity", 1),
            )
            self.session.add(order_item)

        await self.session.flush()
        return order

    async def get_by_id_with_items(self, order_id: str) -> Order | None:
        query = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def get_user_orders(self, user_id: int, limit: int = 10, offset: int = 0) -> list[Order]:
        query = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Order.items))
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_recent_orders(self, limit: int = 20) -> list[Order]:
        """Fetch recent completed or active orders for admin dashboard."""
        query = (
            select(Order)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .options(selectinload(Order.items), selectinload(Order.user))
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_overall_metrics(self) -> dict:
        """Fetch total orders and total revenue for completed orders."""
        from sqlalchemy import func
        count_q = select(func.count(Order.id))
        count_res = await self.session.execute(count_q)
        total_orders = count_res.scalar() or 0

        rev_q = select(func.coalesce(func.sum(Order.total_amount), Decimal("0.00"))).where(
            Order.status == OrderStatus.COMPLETED
        )
        rev_res = await self.session.execute(rev_q)
        total_revenue = rev_res.scalar() or Decimal("0.00")

        return {
            "total_orders": total_orders,
            "total_revenue": Decimal(str(total_revenue)),
        }
