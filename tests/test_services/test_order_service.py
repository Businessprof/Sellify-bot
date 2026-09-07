from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DeliveryType, InventoryStatus, OrderStatus
from app.core.exceptions import InsufficientBalanceError, OutOfStockError
from app.database.models.inventory import InventoryItem
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.models.user import User
from app.services.order_service import OrderService


@pytest.mark.asyncio
async def test_order_purchase_success(db_session: AsyncSession, sample_user: User):
    # Setup product and variant
    cat = ProductCategory(name="AI Tools", slug="ai-cat", icon="🤖")
    db_session.add(cat)
    await db_session.flush()

    prod = Product(
        category_id=cat.id,
        name="Gemini AI Pro 18 Month",
        slug="gemini-18m",
        description="Full access",
        delivery_type=DeliveryType.AUTO_SERIAL,
    )
    db_session.add(prod)
    await db_session.flush()

    variant = ProductVariant(
        product_id=prod.id,
        name="18 Month Access",
        price=Decimal("0.55"),
    )
    db_session.add(variant)
    await db_session.flush()

    item = InventoryItem(
        product_id=prod.id,
        variant_id=variant.id,
        payload="LICENSE-KEY-GEMINI-TEST-001",
        status=InventoryStatus.AVAILABLE,
    )
    db_session.add(item)
    await db_session.commit()

    order_service = OrderService(db_session)
    order, items = await order_service.execute_purchase(
        user_id=sample_user.id,
        variant_id=variant.id,
        quantity=1,
    )
    await db_session.commit()

    assert order.status == OrderStatus.COMPLETED
    assert order.total_amount == Decimal("0.55")
    assert "LICENSE-KEY-GEMINI-TEST-001" in order.delivery_content
    assert items[0].status == InventoryStatus.SOLD

    # Verify wallet debited
    from app.database.repositories.wallet_repo import WalletRepository
    wallet_repo = WalletRepository(db_session)
    wallet = await wallet_repo.get_by_user_id(sample_user.id)
    assert wallet.balance == Decimal("99.45")


@pytest.mark.asyncio
async def test_order_purchase_insufficient_funds(db_session: AsyncSession, sample_user: User):
    # Set user balance to 0
    from app.database.repositories.wallet_repo import WalletRepository
    wallet_repo = WalletRepository(db_session)
    wallet = await wallet_repo.get_by_user_id(sample_user.id)
    wallet.balance = Decimal("0.00")
    await db_session.commit()

    cat = ProductCategory(name="VPN", slug="vpn-cat", icon="🛡️")
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Nord VPN", slug="nord-vpn", description="VPN", delivery_type=DeliveryType.AUTO_ACCOUNT)
    db_session.add(prod)
    await db_session.flush()

    variant = ProductVariant(product_id=prod.id, name="3 Month", price=Decimal("2.99"))
    db_session.add(variant)
    await db_session.flush()

    item = InventoryItem(product_id=prod.id, variant_id=variant.id, payload="user:pass", status=InventoryStatus.AVAILABLE)
    db_session.add(item)
    await db_session.commit()

    order_service = OrderService(db_session)
    with pytest.raises(InsufficientBalanceError):
        await order_service.execute_purchase(user_id=sample_user.id, variant_id=variant.id, quantity=1)

    # Item must still be AVAILABLE
    await db_session.refresh(item)
    assert item.status == InventoryStatus.AVAILABLE


@pytest.mark.asyncio
async def test_order_purchase_out_of_stock(db_session: AsyncSession, sample_user: User):
    cat = ProductCategory(name="Software", slug="sw-cat", icon="💻")
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Lovable Lite", slug="lovable-lite", description="AI builder", delivery_type=DeliveryType.AUTO_ACCOUNT)
    db_session.add(prod)
    await db_session.flush()

    variant = ProductVariant(product_id=prod.id, name="12 Month Lite", price=Decimal("9.50"))
    db_session.add(variant)
    await db_session.commit()

    order_service = OrderService(db_session)
    with pytest.raises(OutOfStockError):
        await order_service.execute_purchase(user_id=sample_user.id, variant_id=variant.id, quantity=1)
