from decimal import Decimal
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models.user import User
from app.database.repositories.user_repo import UserRepository
from app.services.membership_service import MembershipService
from app.services.referral_service import ReferralService
from app.bot.keyboards.menu import get_main_menu_keyboard, get_membership_gate_keyboard

router = Router(name="start_router")


def format_welcome_message(
    user: User,
    balance: Decimal,
    total_spent: Decimal,
    referral_count: int,
    referral_earnings: Decimal,
    referral_link: str,
) -> str:
    username_str = f"@{user.username}" if user.username else "None"
    tier_badge = user.membership_tier.badge
    curr = settings.CURRENCY_SYMBOL

    return (
        "🆀 🅰 🅼 🅸 🅵 🆈\n\n"
        f"👋 Welcome back, <b>{user.first_name}</b>!\n"
        "<i>Quality products at cheapest rates</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ Username: {username_str}\n"
        f"🆔 UserID: <code>{user.id}</code>\n"
        f"👑 Membership: {tier_badge}\n"
        f"💰 Balance: {curr}{balance:.2f}\n"
        f"💎 Total Spent: {curr}{total_spent:.2f}\n"
        f"🤝 Refferals: {referral_count}\n"
        f"💸 Refferal Earning: {curr}{referral_earnings:.2f}\n"
        f"🔗 Refferal Link: {referral_link}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Choose an option below to get started.</i>"
    )


GATE_MESSAGE_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔒 <b>Membership Required</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "To use this bot, please join our channel & group first, then tap ✅ <b>I have joined</b>."
)


@router.message(CommandStart())
async def handle_start(message: Message, bot: Bot, session: AsyncSession, db_user: User):
    membership_service = MembershipService(session)
    is_verified, missing_channels = await membership_service.verify_user_membership(bot, message.from_user.id)

    if not is_verified:
        keyboard = get_membership_gate_keyboard(missing_channels)
        await message.answer(
            GATE_MESSAGE_TEXT,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    # User is verified - display Main Dashboard
    await show_dashboard(message, session, db_user)


@router.callback_query(F.data == "verify_membership")
async def handle_verify_membership(callback: CallbackQuery, bot: Bot, session: AsyncSession, db_user: User):
    membership_service = MembershipService(session)
    is_verified, missing_channels = await membership_service.verify_user_membership(bot, callback.from_user.id)

    if not is_verified:
        await callback.answer("❌ You have not joined all required channels/groups yet!", show_alert=True)
        return

    await callback.answer("✅ Verified — welcome!", show_alert=True)
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_dashboard(callback.message, session, db_user)


async def show_dashboard(message: Message, session: AsyncSession, user: User):
    user_repo = UserRepository(session)
    referral_service = ReferralService(session)

    # Refresh user wallet & stats
    user_with_wallet = await user_repo.get_by_telegram_id(user.id, load_wallet=True)
    balance = user_with_wallet.wallet.balance if user_with_wallet and user_with_wallet.wallet else Decimal("0.00")
    total_spent = await user_repo.get_total_spent(user.id)
    ref_count, ref_earnings = await referral_service.get_referral_stats(user.id)
    ref_link = referral_service.generate_referral_link(user.referral_code)

    text = format_welcome_message(
        user=user,
        balance=balance,
        total_spent=total_spent,
        referral_count=ref_count,
        referral_earnings=ref_earnings,
        referral_link=ref_link,
    )
    keyboard = get_main_menu_keyboard()

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
