from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DeliveryType, InventoryStatus, MembershipTier, OrderStatus, UserRole
from app.database.models.inventory import InventoryItem
from app.database.models.order import Order
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.models.user import User
from app.database.models.wallet import Wallet


@pytest.mark.asyncio
async def test_create_user_and_wallet(db_session: AsyncSession):
    user = User(
        id=1122334455,
        first_name="Alice",
        username="alice_dev",
        membership_tier=MembershipTier.SILVER,
        role=UserRole.USER,
        referral_code="REFALICE123",
    )
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(
        user_id=user.id,
        balance=Decimal("50.00"),
        total_deposited=Decimal("50.00"),
        total_spent=Decimal("0.00"),
    )
    db_session.add(wallet)
    await db_session.commit()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    res = await db_session.execute(
        select(User).where(User.id == 1122334455).options(selectinload(User.wallet))
    )
    saved_user = res.scalar_one()
    assert saved_user is not None
    assert saved_user.first_name == "Alice"
    assert saved_user.wallet is not None
    assert saved_user.wallet.balance == Decimal("50.00")


@pytest.mark.asyncio
async def test_self_referral_constraint(db_session: AsyncSession):
    user = User(
        id=999999,
        first_name="Bob",
        referral_code="REFBOB999",
        referred_by_id=999999,  # Self referral
    )
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_product_and_inventory_relationship(db_session: AsyncSession):
    category = ProductCategory(name="AI Tools", slug="ai-tools", icon="🤖")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        category_id=category.id,
        name="Gemini AI Pro",
        slug="gemini-ai-pro",
        description="18 Month Subscription",
        delivery_type=DeliveryType.AUTO_SERIAL,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        name="18 Month Access",
        price=Decimal("49.99"),
    )
    db_session.add(variant)
    await db_session.flush()

    item = InventoryItem(
        product_id=product.id,
        variant_id=variant.id,
        payload="LICENSE-KEY-ABC-123-XYZ",
        status=InventoryStatus.AVAILABLE,
    )
    db_session.add(item)
    await db_session.commit()

    saved_item = await db_session.get(InventoryItem, item.id)
    assert saved_item is not None
    assert saved_item.status == InventoryStatus.AVAILABLE
    assert saved_item.variant.name == "18 Month Access"
    assert saved_item.variant.product.name == "Gemini AI Pro"
