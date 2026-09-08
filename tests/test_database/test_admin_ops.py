from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DeliveryType, InventoryStatus
from app.database.models.inventory import InventoryItem
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.repositories.inventory_repo import InventoryRepository
from app.database.repositories.product_repo import ProductRepository


@pytest.mark.asyncio
async def test_admin_bulk_add_stock(db_session: AsyncSession):
    cat = ProductCategory(name="Testing", slug="test-cat", icon="🧪")
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Test Product", slug="test-prod", description="Desc", delivery_type=DeliveryType.AUTO_SERIAL)
    db_session.add(prod)
    await db_session.flush()

    var = ProductVariant(product_id=prod.id, name="1 Month", price=Decimal("5.00"))
    db_session.add(var)
    await db_session.commit()

    inv_repo = InventoryRepository(db_session)
    keys_to_add = [
        "KEY-TEST-001",
        "KEY-TEST-002",
        "KEY-TEST-003",
        "",  # Empty line should be ignored
        "  ",
        "KEY-TEST-004",
    ]

    added = await inv_repo.bulk_add_stock(product_id=prod.id, variant_id=var.id, payloads=keys_to_add)
    await db_session.commit()

    assert added == 4
    prod_repo = ProductRepository(db_session)
    stock_count = await prod_repo.get_variant_stock_count(var.id)
    assert stock_count == 4


@pytest.mark.asyncio
async def test_admin_delete_stock_item(db_session: AsyncSession):
    cat = ProductCategory(name="Testing", slug="test-cat-del", icon="🧪")
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Test Item", slug="test-item-del", description="Desc", delivery_type=DeliveryType.LICENSE_KEY)
    db_session.add(prod)
    await db_session.flush()

    var = ProductVariant(product_id=prod.id, name="Standard", price=Decimal("2.50"))
    db_session.add(var)
    await db_session.flush()

    item = InventoryItem(product_id=prod.id, variant_id=var.id, payload="SINGLE-KEY-123", status=InventoryStatus.AVAILABLE)
    db_session.add(item)
    await db_session.commit()

    inv_repo = InventoryRepository(db_session)
    deleted = await inv_repo.delete_stock_item(item.id)
    await db_session.commit()

    assert deleted is True
    prod_repo = ProductRepository(db_session)
    count = await prod_repo.get_variant_stock_count(var.id)
    assert count == 0


@pytest.mark.asyncio
async def test_admin_toggle_and_delete_product(db_session: AsyncSession):
    cat = ProductCategory(name="Testing", slug="test-cat-tog", icon="🧪")
    db_session.add(cat)
    await db_session.flush()

    prod_repo = ProductRepository(db_session)
    prod, var = await prod_repo.create_product_with_variant(
        category_id=cat.id,
        name="Temporary Software",
        slug="temp-soft",
        description="To be deleted",
        delivery_type=DeliveryType.AUTO_ACCOUNT,
        variant_name="Standard",
        price=Decimal("9.99"),
    )
    await db_session.commit()

    assert prod.is_active is True

    # Toggle active
    new_status = await prod_repo.toggle_product_status(prod.id)
    await db_session.commit()
    assert new_status is False

    # Update price
    price_updated = await prod_repo.update_variant_price(var.id, Decimal("12.99"))
    await db_session.commit()
    assert price_updated is True

    # Delete product
    deleted = await prod_repo.delete_product(prod.id)
    await db_session.commit()
    assert deleted is True

    found = await prod_repo.get_product_by_id(prod.id)
    assert found is None
