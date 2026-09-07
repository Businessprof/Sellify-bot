from decimal import Decimal
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import get_back_keyboard
from app.core.config import settings
from app.core.constants import TransactionType
from app.database.models.user import User
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.wallet_repo import WalletRepository

router = Router(name="wallet_payment_router")


@router.callback_query(F.data == "pay_binance")
async def handle_pay_binance(callback: CallbackQuery):
    await callback.answer()
    kb = get_back_keyboard("nav_wallet")
    text = (
        "🔶 <b>Binance Pay Top-Up</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "To deposit funds via Binance Pay:\n\n"
        "1. Open your <b>Binance App</b> → Pay\n"
        "2. Send to Binance Pay ID:\n"
        "   <code>984726183</code>\n"
        "3. Send your Payment TXID / Order ID to Support for instant wallet credit.\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <i>Automated webhooks with instant auto-credit available in production.</i>"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "pay_usdt")
async def handle_pay_usdt(callback: CallbackQuery):
    await callback.answer()
    kb = get_back_keyboard("nav_wallet")
    text = (
        "₮ <b>USDT (BEP-20 · Binance Smart Chain)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Send USDT (BEP-20) to the address below:\n\n"
        "<code>0x71C5696d03D5154388eDb4538FE95d9A726aA51E</code>\n\n"
        "⚠️ <b>Network:</b> BSC (BNB Smart Chain - BEP20)\n"
        "⏱ <b>Confirmations:</b> 3 Network Confirmations\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Once confirmed, send the hash to support or wait for automatic credit.</i>"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "wallet_redeem")
async def handle_wallet_redeem(callback: CallbackQuery):
    await callback.answer("Redeem voucher feature", show_alert=False)
    kb = get_back_keyboard("nav_wallet")
    text = (
        "🎉 <b>Redeem Voucher / Gift Code</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Have a promotional or deposit code?\n"
        "Send the code in the chat, e.g.:\n"
        "<code>/redeem CODE123</code>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "wallet_history")
async def handle_wallet_history(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    wallet_repo = WalletRepository(session)
    transactions = await wallet_repo.get_transactions(db_user.id, limit=8)

    kb = get_back_keyboard("nav_wallet")
    if not transactions:
        text = (
            "📒 <b>Transaction History</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>No transactions recorded yet.</i>"
        )
    else:
        lines = ["📒 <b>Recent Transactions:</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for tx in transactions:
            sign = "+" if tx.amount > 0 else ""
            lines.append(
                f"• <b>{tx.type.value}</b>: <code>{sign}${tx.amount:.2f}</code>\n"
                f"  <i>{tx.description}</i> ({tx.created_at.strftime('%m/%d %H:%M')})"
            )
        text = "\n\n".join(lines)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "profile_orders")
async def handle_profile_orders(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    order_repo = OrderRepository(session)
    orders = await order_repo.get_user_orders(db_user.id, limit=5)

    kb = get_back_keyboard("nav_profile")
    if not orders:
        text = (
            "📦 <b>My Orders</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>You haven't placed any orders yet.</i>\n\n"
            "Visit 🛍️ <b>SHOP</b> to browse products!"
        )
    else:
        lines = ["📦 <b>Your Recent Orders:</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for o in orders:
            content_preview = (
                f"\n  📬 <code>{o.delivery_content}</code>" if o.delivery_content else ""
            )
            lines.append(
                f"• <b>{o.order_number}</b> | <b>${o.total_amount:.2f}</b>\n"
                f"  Status: <code>{o.status.value}</code>"
                f"{content_preview}"
            )
        text = "\n\n".join(lines)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "view_membership_tiers")
async def handle_view_membership_tiers(callback: CallbackQuery):
    await callback.answer()
    kb = get_back_keyboard("nav_profile")
    text = (
        "🏆 <b>Membership Tiers & Perks</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Unlock permanent store-wide discounts based on your total spend:\n\n"
        "🥉 <b>Bronze</b> — $0+ Spent\n"
        "• Default Member Status\n\n"
        "🥈 <b>Silver</b> — $50+ Spent\n"
        "• <b>2% OFF</b> all purchases\n\n"
        "🥇 <b>Gold</b> — $200+ Spent\n"
        "• <b>5% OFF</b> all purchases\n\n"
        "💎 <b>Diamond</b> — $500+ Spent\n"
        "• <b>10% OFF</b> all purchases + Priority Support\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
