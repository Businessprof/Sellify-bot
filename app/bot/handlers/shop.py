from decimal import Decimal
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientBalanceError, OutOfStockError
from app.database.models.user import User
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.wallet_repo import WalletRepository
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService

router = Router(name="shop_router")


@router.callback_query(F.data.startswith("buy_variant_"))
async def handle_view_product_variant(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    variant_id = int(callback.data.split("buy_variant_")[1])
    product_repo = ProductRepository(session)
    wallet_repo = WalletRepository(session)

    variant = await product_repo.get_variant_by_id(variant_id)
    if not variant:
        await callback.answer("Product not found.", show_alert=True)
        return

    stock = await product_repo.get_variant_stock_count(variant.id)
    wallet = await wallet_repo.get_by_user_id(db_user.id)
    user_balance = wallet.balance if wallet else Decimal("0.00")

    buttons = []
    if stock > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🛒 Buy Now (${variant.price:.2f})",
                    callback_data=f"confirm_buy_{variant.id}",
                )
            ]
        )
    else:
        buttons.append([InlineKeyboardButton(text="❌ Out of Stock", callback_data="none")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back to Shop", callback_data="nav_shop")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        f"📦 <b>{variant.product.name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <b>Option:</b> {variant.name}\n"
        f"💰 <b>Price:</b> <code>${variant.price:.2f}</code>\n"
        f"📦 <b>Stock:</b> <code>{stock}</code>\n"
        f"💳 <b>Your Balance:</b> <code>${user_balance:.2f}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Description:</b>\n{variant.product.description}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("confirm_buy_"))
async def handle_confirm_purchase(callback: CallbackQuery, bot: Bot, session: AsyncSession, db_user: User):
    variant_id = int(callback.data.split("confirm_buy_")[1])
    order_service = OrderService(session)
    product_repo = ProductRepository(session)
    notification_service = NotificationService(bot)

    variant = await product_repo.get_variant_by_id(variant_id)
    if not variant:
        await callback.answer("Product not found.", show_alert=True)
        return

    try:
        order, items = await order_service.execute_purchase(
            user_id=db_user.id,
            variant_id=variant_id,
            quantity=1,
        )
        await session.commit()
    except InsufficientBalanceError as e:
        await callback.answer("❌ Insufficient wallet balance!", show_alert=True)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Add Funds to Wallet", callback_data="nav_wallet")],
                [InlineKeyboardButton(text="⬅️ Back to Shop", callback_data="nav_shop")],
            ]
        )
        if callback.message:
            await callback.message.edit_text(
                f"❌ <b>Insufficient Funds!</b>\n\n"
                f"You need <b>${e.required:.2f}</b>, but your balance is <b>${e.current:.2f}</b>.\n"
                "Please add funds to your wallet to complete this purchase.",
                reply_markup=kb,
                parse_mode="HTML",
            )
        return
    except OutOfStockError:
        await callback.answer("⚠️ Item just went out of stock!", show_alert=True)
        return

    # Broadcast to live sales channel (Screenshot 2)
    customer_display = db_user.username or db_user.first_name
    await notification_service.broadcast_live_purchase(
        customer_name=customer_display,
        product_name=f"{variant.product.name} ({variant.name})",
        quantity=1,
        variant_id=variant.id,
    )

    # Success delivery view
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 View My Orders", callback_data="profile_orders")],
            [InlineKeyboardButton(text="🛍️ Continue Shopping", callback_data="nav_shop")],
        ]
    )

    receipt_text = (
        "✅ <b>Order Successful & Delivered!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Order ID:</b> <code>{order.order_number}</code>\n"
        f"📦 <b>Product:</b> {variant.product.name} — {variant.name}\n"
        f"💰 <b>Total Paid:</b> <code>${order.total_amount:.2f}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📬 <b>Your Digital Product:</b>\n\n"
        f"<code>{order.delivery_content}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>Please save this information safely. You can also view it anytime under Profile → Orders.</i>"
    )

    await callback.answer("🎉 Purchase completed!", show_alert=False)
    if callback.message:
        await callback.message.edit_text(receipt_text, reply_markup=kb, parse_mode="HTML")
