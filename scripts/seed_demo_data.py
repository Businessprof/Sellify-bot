import asyncio
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.constants import DeliveryType, InventoryStatus
from app.core.logger import logger
from app.database.models.inventory import InventoryItem
from app.database.models.product import Product, ProductCategory, ProductVariant
from app.database.models.user import MembershipChannel
from app.database.session import async_session_maker, init_db


PRODUCTS_FROM_SCREENSHOT_5 = [
    # (Category slug, Product Name, Variant Name, Price, Stock Count, Delivery Type, Description)
    (
        "ai-tools",
        "Gemini AI Pro 18 Month",
        "18 Month Access",
        Decimal("0.55"),
        748,
        DeliveryType.AUTO_SERIAL,
        "Google Gemini Advanced 18 Month Full Access with 2TB Cloud Storage.",
    ),
    (
        "software",
        "Capcut Pro 1 Month",
        "1 Month Access",
        Decimal("1.60"),
        4,
        DeliveryType.AUTO_ACCOUNT,
        "CapCut Pro Desktop & Mobile 1 Month Subscription Account.",
    ),
    (
        "streaming",
        "Netflix Premium 4K UHD Full Admin Account",
        "1 Month Private Admin",
        Decimal("1.50"),
        12,
        DeliveryType.AUTO_ACCOUNT,
        "Netflix 4K UHD 4-Screen Full Admin Private Credentials.",
    ),
    (
        "streaming",
        "Amazon Prime Video 6 Month",
        "6 Month Account",
        Decimal("1.50"),
        12,
        DeliveryType.AUTO_ACCOUNT,
        "Amazon Prime Video 6 Months HD streaming subscription.",
    ),
    (
        "software",
        "Lovable Lite 12m Account",
        "12 Month Lite",
        Decimal("9.50"),
        0,  # Out of stock as seen in Screenshot 5
        DeliveryType.AUTO_ACCOUNT,
        "Lovable Lite Full-stack AI builder annual subscription.",
    ),
    (
        "vpn-services",
        "Surfshark 2 month Coupons",
        "2 Month Promo Code",
        Decimal("0.70"),
        462,
        DeliveryType.LICENSE_KEY,
        "Surfshark 2 Months Unlimited Devices Promo Coupon Code.",
    ),
    (
        "streaming",
        "SPOTIFY PREMIUM 2M",
        "2 Month Individual",
        Decimal("1.50"),
        3,
        DeliveryType.AUTO_ACCOUNT,
        "Spotify Premium 2 Month Ad-Free High Fidelity Audio.",
    ),
    (
        "vpn-services",
        "Surfshark VPN 2M Private Accounts",
        "2 Month Private Account",
        Decimal("2.00"),
        6,
        DeliveryType.AUTO_ACCOUNT,
        "Surfshark VPN 2 Month Private Account credentials.",
    ),
    (
        "ai-tools",
        "LEONARDO AI VIDEO GEN",
        "1 Month Tier",
        Decimal("0.70"),
        3,
        DeliveryType.AUTO_ACCOUNT,
        "Leonardo.ai Video Generation with daily token allowance.",
    ),
    (
        "vpn-services",
        "Nord VPN 3 Month Accounts",
        "3 Month Account",
        Decimal("2.99"),
        5,
        DeliveryType.AUTO_ACCOUNT,
        "NordVPN 3 Month High Speed Servers & Double Encryption.",
    ),
    (
        "software",
        "Udemy Personal Plan 1M",
        "1 Month Subscription",
        Decimal("1.50"),
        5,
        DeliveryType.AUTO_ACCOUNT,
        "Udemy Personal Plan 1 Month Unlimited Courses Access.",
    ),
    (
        "ai-tools",
        "Super Grok 7 Days",
        "7 Day Access",
        Decimal("3.50"),
        2,
        DeliveryType.AUTO_ACCOUNT,
        "xAI Super Grok 2 Ultra fast AI intelligence 7-day access.",
    ),
    (
        "ai-tools",
        "Perplexity Enterprise Pro 1m",
        "1 Month Pro",
        Decimal("6.00"),
        2,
        DeliveryType.AUTO_ACCOUNT,
        "Perplexity Enterprise Pro with Claude 3.5 Sonnet & GPT-4o.",
    ),
    (
        "software",
        "Notion Business 3 month Coupon",
        "3 Month Coupon",
        Decimal("2.00"),
        12,
        DeliveryType.LICENSE_KEY,
        "Notion Business Plan 3 Month upgrade voucher code.",
    ),
    (
        "vpn-services",
        "HMA VPN Monthly Licence Key",
        "1 Month License",
        Decimal("0.80"),
        2,
        DeliveryType.LICENSE_KEY,
        "HideMyAss (HMA) VPN 1 Month Official License Activation Key.",
    ),
    (
        "emails-trials",
        "Outlook Mail",
        "1x Fresh Account",
        Decimal("0.05"),
        962,
        DeliveryType.AUTO_ACCOUNT,
        "Fresh Outlook / Hotmail email account with POP3/IMAP enabled.",
    ),
    (
        "software",
        "API Orders Test",
        "Test Item",
        Decimal("0.01"),
        5,
        DeliveryType.AUTO_SERIAL,
        "Sandbox test item for reseller API integration.",
    ),
]


async def seed_data():
    logger.info("Initializing database schema...")
    await init_db()

    async with async_session_maker() as session:
        # 1. Seed Mandatory Channels
        res = await session.execute(select(MembershipChannel))
        if not res.scalars().first():
            logger.info("Seeding membership channels...")
            channel = MembershipChannel(
                title="Sellify Announcements",
                channel_id=settings.MANDATORY_CHANNEL_ID,
                invite_link=settings.MANDATORY_CHANNEL_LINK,
                is_mandatory=True,
                is_active=True,
            )
            group = MembershipChannel(
                title="Sellify Community Group",
                channel_id=settings.MANDATORY_GROUP_ID,
                invite_link=settings.MANDATORY_GROUP_LINK,
                is_mandatory=True,
                is_active=True,
            )
            session.add_all([channel, group])

        # 2. Seed Categories
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
            cat_res = await session.execute(select(ProductCategory).where(ProductCategory.slug == slug))
            cat = cat_res.scalar_one_or_none()
            if not cat:
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
                await session.flush()
            category_map[slug] = cat

        # 3. Clear existing items and repopulate exact 17 items from Screenshot 5
        await session.execute(delete(InventoryItem))
        await session.execute(delete(ProductVariant))
        await session.execute(delete(Product))
        await session.flush()

        logger.info(f"Seeding {len(PRODUCTS_FROM_SCREENSHOT_5)} items matching Screenshot 5...")
        for idx, (cat_slug, prod_name, var_name, price, stock, delivery_type, desc) in enumerate(PRODUCTS_FROM_SCREENSHOT_5):
            product = Product(
                category_id=category_map[cat_slug].id,
                name=prod_name,
                slug=f"prod-{idx}-{cat_slug}",
                description=desc,
                delivery_type=delivery_type,
                is_active=True,
                is_trial_or_email=(cat_slug == "emails-trials"),
            )
            session.add(product)
            await session.flush()

            variant = ProductVariant(
                product_id=product.id,
                name=var_name,
                price=price,
                display_order=idx,
                is_active=True,
            )
            session.add(variant)
            await session.flush()

            # Seed stock items
            for i in range(1, stock + 1):
                if delivery_type == DeliveryType.LICENSE_KEY:
                    payload = f"KEY-{prod_name[:6].upper()}-{i:04d}-XXXX-YYYY"
                elif delivery_type == DeliveryType.AUTO_ACCOUNT:
                    payload = f"{prod_name[:4].lower()}_{i:03d}@secure-login.com : SafePass{i:03d}!"
                else:
                    payload = f"SERIAL-{prod_name[:5].upper()}-{i:04d}-TOKEN-ACCESS"

                item = InventoryItem(
                    product_id=product.id,
                    variant_id=variant.id,
                    payload=payload,
                    status=InventoryStatus.AVAILABLE,
                )
                session.add(item)

        await session.commit()
        logger.info("All 17 items from Screenshot 5 seeded successfully with inventory stock!")


if __name__ == "__main__":
    asyncio.run(seed_data())
