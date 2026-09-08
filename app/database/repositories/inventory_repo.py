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

    async def bulk_add_stock(self, product_id: int, variant_id: int, payloads: list[str]) -> int:
        """Add multiple inventory items (keys/accounts) at once."""
        valid_payloads = [p.strip() for p in payloads if p.strip()]
        if not valid_payloads:
            return 0

        for payload in valid_payloads:
            item = InventoryItem(
                product_id=product_id,
                variant_id=variant_id,
                payload=payload,
                status=InventoryStatus.AVAILABLE,
            )
            self.session.add(item)

        await self.session.flush()
        return len(valid_payloads)

    async def delete_stock_item(self, item_id: str) -> bool:
        """Delete an individual inventory item."""
        item = await self.session.get(InventoryItem, item_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def get_variant_items(
        self, variant_id: int, status: InventoryStatus | None = None, limit: int = 50
    ) -> list[InventoryItem]:
        """Fetch stock items for a given variant with optional status filter."""
        query = select(InventoryItem).where(InventoryItem.variant_id == variant_id)
        if status:
            query = query.where(InventoryItem.status == status)
        query = query.order_by(InventoryItem.created_at.desc()).limit(limit)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def count_all_available_stock(self) -> int:
        """Count total available stock items across all products."""
        from sqlalchemy import func
        res = await self.session.execute(
            select(func.count(InventoryItem.id)).where(InventoryItem.status == InventoryStatus.AVAILABLE)
        )
        return res.scalar() or 0
