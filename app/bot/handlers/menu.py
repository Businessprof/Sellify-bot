from decimal import Decimal
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import show_dashboard
from app.bot.keyboards.common import get_back_keyboard
from app.core.config import settings
from app.core.security import generate_api_key
from app.database.models.audit import ApiKey
from app.database.models.user import User
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.wallet_repo import WalletRepository
from app.services.referral_service import ReferralService

router = Router(name="menu_router")


@router.callback_query(F.data == "nav_main_menu")
async def handle_back_to_menu(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_dashboard(callback.message, session, db_user)


@router.callback_query(F.data == "nav_shop")
async def handle_nav_shop(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    product_repo = ProductRepository(session)
    categories = await product_repo.get_active_categories()

    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"{cat.icon} {cat.name}", callback_data=f"cat_{cat.id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="nav_main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        "🛍️ <b>Digital Products Catalog</b>\n\n"
        "Select a category below to browse available software, streaming services, accounts, and subscriptions:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_wallet")
async def handle_nav_wallet(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    wallet_repo = WalletRepository(session)
    wallet = await wallet_repo.get_by_user_id(db_user.id)
    balance = wallet.balance if wallet else Decimal("0.00")
    curr = settings.CURRENCY_SYMBOL

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Add Funds", callback_data="wallet_add_funds"),
                InlineKeyboardButton(text="📜 Transactions", callback_data="wallet_history"),
            ],
            [
                InlineKeyboardButton(text="🎁 Redeem Code", callback_data="wallet_redeem"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu"),
            ],
        ]
    )

    text = (
        "💳 <b>Your Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Current Balance:</b> <code>{curr}{balance:.2f}</code>\n"
        f"📥 <b>Total Deposited:</b> <code>{curr}{wallet.total_deposited:.2f}</code>\n"
        f"📤 <b>Total Spent:</b> <code>{curr}{wallet.total_spent:.2f}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Add funds instantly or redeem voucher codes."
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_freebies")
async def handle_nav_freebies(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Claim Daily Bonus", callback_data="claim_daily_freebie")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")],
        ]
    )
    text = (
        "🎁 <b>Freebies & Rewards</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Claim free trial products, wallet bonuses, and loyalty rewards daily!\n\n"
        "<i>Check back every 24 hours to claim your perks.</i>"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_profile")
async def handle_nav_profile(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    user_repo = UserRepository(session)
    referral_service = ReferralService(session)

    user_with_wallet = await user_repo.get_by_telegram_id(db_user.id, load_wallet=True)
    balance = user_with_wallet.wallet.balance if user_with_wallet and user_with_wallet.wallet else Decimal("0.00")
    total_spent = await user_repo.get_total_spent(db_user.id)
    ref_count, ref_earnings = await referral_service.get_referral_stats(db_user.id)
    curr = settings.CURRENCY_SYMBOL

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 My Orders", callback_data="profile_orders")],
            [InlineKeyboardButton(text="🎯 Referrals", callback_data="nav_referral_store")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")],
        ]
    )

    text = (
        "🙂 <b>User Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {db_user.first_name}\n"
        f"🏷️ <b>Username:</b> @{db_user.username or 'None'}\n"
        f"🆔 <b>Telegram ID:</b> <code>{db_user.id}</code>\n"
        f"👑 <b>Tier:</b> {db_user.membership_tier.badge}\n"
        f"💰 <b>Balance:</b> {curr}{balance:.2f}\n"
        f"💎 <b>Total Spent:</b> {curr}{total_spent:.2f}\n"
        f"🤝 <b>Referrals:</b> {ref_count}\n"
        f"💸 <b>Referral Earnings:</b> {curr}{ref_earnings:.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_referral_store")
async def handle_nav_referral_store(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    referral_service = ReferralService(session)
    ref_count, ref_earnings = await referral_service.get_referral_stats(db_user.id)
    ref_link = referral_service.generate_referral_link(db_user.referral_code)
    curr = settings.CURRENCY_SYMBOL

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 10 Referrals: $10 Bonus", callback_data="redeem_ref_10")],
            [InlineKeyboardButton(text="🔥 50 Referrals: Premium Product", callback_data="redeem_ref_50")],
            [InlineKeyboardButton(text="🔥 100 Referrals: $100 Bonus", callback_data="redeem_ref_100")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")],
        ]
    )

    text = (
        "🎯 <b>Referral Program & Store</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤝 <b>Your Referrals:</b> {ref_count}\n"
        f"💸 <b>Total Earned:</b> {curr}{ref_earnings:.2f}\n"
        f"🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>\n\n"
        f"Earn <b>{settings.DEFAULT_REFERRAL_COMMISSION_PERCENT}% lifetime commission</b> on every purchase made by your referrals!\n"
        "Milestone rewards can also be unlocked below:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_support")
async def handle_nav_support(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Payment Problem", callback_data="ticket_cat_payment")],
            [InlineKeyboardButton(text="📦 Order Problem", callback_data="ticket_cat_order")],
            [InlineKeyboardButton(text="🔐 Account Problem", callback_data="ticket_cat_account")],
            [InlineKeyboardButton(text="❓ Other Issue", callback_data="ticket_cat_other")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")],
        ]
    )
    text = (
        "🛟 <b>24/7 Support Desk</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Need help with a purchase or have questions? Select a category below to submit a support ticket:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_trials")
async def handle_nav_trials(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    product_repo = ProductRepository(session)
    # Search for categories or products flagged as trials
    categories = await product_repo.get_active_categories()
    buttons = []
    for cat in categories:
        if "trial" in cat.name.lower() or "email" in cat.name.lower():
            buttons.append([InlineKeyboardButton(text=f"{cat.icon} {cat.name}", callback_data=f"cat_{cat.id}")])

    if not buttons:
        buttons.append([InlineKeyboardButton(text="📦 Browse All Categories", callback_data="nav_shop")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        "📨 <b>Emails & Trials</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Special trial products, verified educational/work emails, and trial account generation services."
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_reseller")
async def handle_nav_reseller(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer()
    user_repo = UserRepository(session)
    user_with_wallet = await user_repo.get_by_telegram_id(db_user.id, load_wallet=True)
    balance = user_with_wallet.wallet.balance if user_with_wallet and user_with_wallet.wallet else Decimal("0.00")
    curr = settings.CURRENCY_SYMBOL

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Generate / Regenerate Key", callback_data="reseller_regen_key")],
            [InlineKeyboardButton(text="📚 API Docs", url="https://example.com/docs")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="nav_main_menu")],
        ]
    )

    text = (
        "🔑 <b>Reseller API Integration</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Automate digital delivery directly through our REST API.\n\n"
        f"💰 <b>Reseller Balance:</b> {curr}{balance:.2f}\n"
        "⚡ <b>Rate Limit:</b> 60 req/min\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Click below to generate or manage your secret reseller API key."
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "reseller_regen_key")
async def handle_reseller_regen_key(callback: CallbackQuery, session: AsyncSession, db_user: User):
    raw_key, prefix, key_hash = generate_api_key()
    api_key_obj = ApiKey(
        user_id=db_user.id,
        key_prefix=prefix,
        key_hash=key_hash,
        is_active=True,
    )
    session.add(api_key_obj)
    await session.flush()

    await callback.answer("🔑 Key generated successfully!", show_alert=True)
    kb = get_back_keyboard("nav_reseller")
    text = (
        "🔑 <b>Your New Reseller API Key:</b>\n\n"
        f"<code>{raw_key}</code>\n\n"
        "⚠️ <i>Please copy and save this key now. For your security, it will never be displayed in full again.</i>"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "nav_clear_chat")
async def handle_clear_chat(callback: CallbackQuery):
    await callback.answer("🧹 Cleaning chat history...", show_alert=False)
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
