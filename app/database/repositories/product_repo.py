from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import InventoryStatus
from app.database.models.inventory import InventoryItem
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_active_categories(self) -> list[ProductCategory]:
        query = (
            select(ProductCategory)
            .where(ProductCategory.is_active == True)  # noqa: E712
            .order_by(ProductCategory.display_order, ProductCategory.name)
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_category_by_id(self, category_id: int) -> ProductCategory | None:
        return await self.session.get(ProductCategory, category_id)

    async def get_products_by_category(
        self, category_id: int, is_trial_or_email: bool = False
    ) -> list[Product]:
        query = (
            select(Product)
            .where(
                Product.category_id == category_id,
                Product.is_active == True,  # noqa: E712
                Product.is_trial_or_email == is_trial_or_email,
            )
            .order_by(Product.name)
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_product_by_id(self, product_id: int, load_variants: bool = True) -> Product | None:
        query = select(Product).where(Product.id == product_id)
        if load_variants:
            query = query.options(selectinload(Product.variants))
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def get_variant_by_id(self, variant_id: int) -> ProductVariant | None:
        query = select(ProductVariant).where(ProductVariant.id == variant_id).options(selectinload(ProductVariant.product))
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def get_variant_stock_count(self, variant_id: int) -> int:
        query = select(func.count(InventoryItem.id)).where(
            InventoryItem.variant_id == variant_id,
            InventoryItem.status == InventoryStatus.AVAILABLE,
        )
        res = await self.session.execute(query)
        return res.scalar() or 0
