import asyncio
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.core.config import settings
from app.core.constants import DeliveryType, InventoryStatus
from app.core.logger import logger
from app.database.models.inventory import InventoryItem
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.models.user import MembershipChannel
from app.database.session import async_session_maker, init_db


async def seed_data():
    logger.info("Initializing database schema...")
    await init_db()

    async with async_session_maker() as session:
        # 1. Seed Mandatory Channels
        res = await session.execute(select(MembershipChannel))
        if not res.scalars().first():
            logger.info("Seeding membership channels...")
            channel = MembershipChannel(
                title="Qamify Announcements",
                channel_id=settings.MANDATORY_CHANNEL_ID,
                invite_link=settings.MANDATORY_CHANNEL_LINK,
                is_mandatory=True,
                is_active=True,
            )
            group = MembershipChannel(
                title="Qamify Community Group",
                channel_id=settings.MANDATORY_GROUP_ID,
                invite_link=settings.MANDATORY_GROUP_LINK,
                is_mandatory=True,
                is_active=True,
            )
            session.add_all([channel, group])

        # 2. Seed Product Categories
        cat_res = await session.execute(select(ProductCategory))
        if not cat_res.scalars().first():
            logger.info("Seeding product categories and items...")
            categories_data = [
                ("🤖 AI Tools", "ai-tools", "Premium AI subscriptions and accounts"),
                ("🛡️ VPN Services", "vpn-services", "High speed private VPNs"),
                ("🎬 Streaming", "streaming", "Prime Video, Netflix, and OTT access"),
                ("💻 Software & OS", "software", "Operating systems and productivity tools"),
                ("🎮 Gaming", "gaming", "Game passes, accounts, and keys"),
                ("📨 Emails & Trials", "emails-trials", "Student and educational trial accounts"),
            ]

            category_map = {}
            for idx, (name, slug, desc) in enumerate(categories_data):
                icon = name.split()[0]
                cat_name = " ".join(name.split()[1:])
                cat = ProductCategory(
                    name=cat_name,
                    slug=slug,
                    icon=icon,
                    description=desc,
                    display_order=idx,
                    is_active=True,
                )
                session.add(cat)
                category_map[slug] = cat

            await session.flush()

            # Seed Gemini AI Pro
            gemini_product = Product(
                category_id=category_map["ai-tools"].id,
                name="Google Gemini AI Pro",
                slug="gemini-ai-pro",
                description="Google Gemini Advanced 18 Month Full Access with 2TB Cloud Storage.",
                delivery_type=DeliveryType.AUTO_SERIAL,
                is_active=True,
            )
            session.add(gemini_product)
            await session.flush()

            v18m = ProductVariant(
                product_id=gemini_product.id,
                name="18 Month Access",
                price=Decimal("19.99"),
                display_order=0,
                is_active=True,
            )
            session.add(v18m)
            await session.flush()

            # Add inventory stock for Gemini
            for i in range(1, 11):
                item = InventoryItem(
                    product_id=gemini_product.id,
                    variant_id=v18m.id,
                    payload=f"GEMINI-PRO-LICENSE-CODE-{i:03d}-ABCXYZ",
                    status=InventoryStatus.AVAILABLE,
                )
                session.add(item)

            # Seed Surfshark VPN
            surfshark = Product(
                category_id=category_map["vpn-services"].id,
                name="Surfshark VPN Premium",
                slug="surfshark-vpn",
                description="Surfshark VPN 24 Month Unlimited Devices Private Credentials.",
                delivery_type=DeliveryType.AUTO_ACCOUNT,
                is_active=True,
            )
            session.add(surfshark)
            await session.flush()

            v2m = ProductVariant(
                product_id=surfshark.id,
                name="2 Month Private Account",
                price=Decimal("4.99"),
                display_order=0,
                is_active=True,
            )
            v24m = ProductVariant(
                product_id=surfshark.id,
                name="24 Month Private Account",
                price=Decimal("24.99"),
                display_order=1,
                is_active=True,
            )
            session.add_all([v2m, v24m])
            await session.flush()

            # Add stock for Surfshark
            for i in range(1, 6):
                item = InventoryItem(
                    product_id=surfshark.id,
                    variant_id=v2m.id,
                    payload=f"user_{i}@surfshark-safe.com : PassSecret{i}#",
                    status=InventoryStatus.AVAILABLE,
                )
                session.add(item)

        await session.commit()
        logger.info("Demo data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
