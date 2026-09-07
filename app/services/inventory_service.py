from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.inventory import InventoryItem
from app.database.repositories.inventory_repo import InventoryRepository
from app.database.repositories.product_repo import ProductRepository


class InventoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory_repo = InventoryRepository(session)
        self.product_repo = ProductRepository(session)

    async def get_stock_count(self, variant_id: int) -> int:
        return await self.product_repo.get_variant_stock_count(variant_id)

    async def reserve_stock(self, variant_id: int, quantity: int = 1) -> list[InventoryItem]:
        return await self.inventory_repo.reserve_stock(variant_id, quantity)

    async def complete_delivery(self, items: list[InventoryItem], order_id: str) -> None:
        await self.inventory_repo.complete_delivery(items, order_id)

    async def release_stock(self, items: list[InventoryItem]) -> None:
        await self.inventory_repo.release_stock(items)
