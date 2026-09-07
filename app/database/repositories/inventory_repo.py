from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InventoryStatus
from app.core.exceptions import OutOfStockError
from app.database.models.inventory import InventoryItem
from app.database.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[InventoryItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(InventoryItem, session)

    async def reserve_stock(self, variant_id: int, quantity: int = 1) -> list[InventoryItem]:
        """
        Safely fetch and reserve inventory items.
        Applies row-level locks on PostgreSQL when available.
        """
        query = (
            select(InventoryItem)
            .where(
                InventoryItem.variant_id == variant_id,
                InventoryItem.status == InventoryStatus.AVAILABLE,
            )
            .limit(quantity)
        )
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        res = await self.session.execute(query)
        items = list(res.scalars().all())

        if len(items) < quantity:
            raise OutOfStockError()

        now = datetime.now(timezone.utc)
        for item in items:
            item.status = InventoryStatus.RESERVED
            item.reserved_at = now

        await self.session.flush()
        return items

    async def complete_delivery(self, items: list[InventoryItem], order_id: str) -> None:
        now = datetime.now(timezone.utc)
        for item in items:
            item.status = InventoryStatus.SOLD
            item.order_id = order_id
            item.sold_at = now
        await self.session.flush()

    async def release_stock(self, items: list[InventoryItem]) -> None:
        for item in items:
            item.status = InventoryStatus.AVAILABLE
            item.reserved_at = None
            item.order_id = None
        await self.session.flush()
