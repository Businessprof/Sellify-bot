from decimal import Decimal
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin_filter import AdminFilter
from app.bot.states.admin_states import AdminPriceStates, AdminStockStates
from app.core.config import settings
from app.database.models.user import User
from app.database.repositories.inventory_repo import InventoryRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.user_repo import UserRepository

router = Router(name="admin_router")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def handle_admin_command(message: Message, session: AsyncSession):
    await show_admin_hub(message, session)


async def show_admin_hub(target: Message, session: AsyncSession):
    user_repo = UserRepository(session)
    order_repo = OrderRepository(session)
    inv_repo = InventoryRepository(session)

    total_users = await user_repo.count_all_users()
    total_stock = await inv_repo.count_all_available_stock()
    metrics = await order_repo.get_overall_metrics()
    curr = settings.CURRENCY_SYMBOL

    text = (
        "🛠️ <b>Sellify Administrator Hub</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"📦 <b>Available Stock:</b> <code>{total_stock} items</code>\n"
        f"🛒 <b>Total Orders:</b> <code>{metrics['total_orders']}</code>\n"
        f"💰 <b>Total Revenue:</b> <code>{curr}{metrics['total_revenue']:.2f}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Select an administrative action below:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Products & Stock Management", callback_data="admin_products")],
            [InlineKeyboardButton(text="📊 Refresh Metrics", callback_data="admin_refresh_metrics")],
            [InlineKeyboardButton(text="🌐 Web Admin URL", callback_data="admin_web_info")],
            [InlineKeyboardButton(text="❌ Close Admin Hub", callback_data="admin_close")],
        ]
    )

    await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_close")
async def handle_admin_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass


@router.callback_query(F.data == "admin_refresh_metrics")
async def handle_admin_refresh_metrics(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("Metrics refreshed!")
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_admin_hub(callback.message, session)


@router.callback_query(F.data == "admin_web_info")
async def handle_admin_web_info(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_hub_back")]
        ]
    )
    text = (
        "🌐 <b>Web Admin Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "You can manage products, bulk paste stock, and inspect live orders in your web browser:\n\n"
        "🔗 <b>Local URL:</b> <code>http://localhost:8000/admin</code>\n"
        "📦 <b>Direct Stock Page:</b> <code>http://localhost:8000/admin/inventory</code>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_hub_back")
async def handle_admin_hub_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    await callback.answer()
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_admin_hub(callback.message, session)


@router.callback_query(F.data == "admin_products")
async def handle_admin_products_list(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    prod_repo = ProductRepository(session)
    products = await prod_repo.get_all_products_with_variants()

    buttons = []
    for p in products:
        for v in p.variants:
            stock = await prod_repo.get_variant_stock_count(v.id)
            status_icon = "🟢" if stock > 0 else "🔴"
            btn_text = f"{status_icon} {p.name} ({v.name}) | 📦 {stock}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_var_{v.id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back to Admin Hub", callback_data="admin_hub_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        "📦 <b>Manage Products & Stock</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Tap any product variant below to <b>Add Stock</b>, <b>Edit Price</b>, or <b>Remove</b> it:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_var_"))
async def handle_admin_variant_details(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    variant_id = int(callback.data.split("adm_var_")[1])
    prod_repo = ProductRepository(session)
    variant = await prod_repo.get_variant_by_id(variant_id)

    if not variant:
        await callback.answer("Variant not found.", show_alert=True)
        return

    stock = await prod_repo.get_variant_stock_count(variant.id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Stock (Paste Keys/Accounts)", callback_data=f"adm_add_stock_{variant.id}")],
            [InlineKeyboardButton(text="✏️ Edit Price", callback_data=f"adm_edit_price_{variant.id}")],
            [InlineKeyboardButton(text="🗑️ Remove / Delete Product", callback_data=f"adm_del_prod_{variant.product.id}")],
            [InlineKeyboardButton(text="⬅️ Back to Products", callback_data="admin_products")],
        ]
    )

    text = (
        f"⚙️ <b>Variant Management</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Product:</b> {variant.product.name}\n"
        f"🏷️ <b>Option:</b> {variant.name}\n"
        f"💰 <b>Price:</b> <code>${variant.price:.2f}</code>\n"
        f"📦 <b>Current Stock:</b> <code>{stock} items</code>\n"
        f"🚚 <b>Delivery Type:</b> <code>{variant.product.delivery_type.value}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an action below:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_add_stock_"))
async def handle_adm_add_stock_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    variant_id = int(callback.data.split("adm_add_stock_")[1])
    prod_repo = ProductRepository(session)
    variant = await prod_repo.get_variant_by_id(variant_id)

    if not variant:
        await callback.answer("Variant not found.", show_alert=True)
        return

    await state.set_state(AdminStockStates.waiting_for_stock_items)
    await state.update_data(product_id=variant.product_id, variant_id=variant.id, variant_name=f"{variant.product.name} ({variant.name})")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"adm_var_{variant.id}")],
        ]
    )

    text = (
        f"📥 <b>Restocking: {variant.product.name}</b>\n"
        f"🏷️ Option: <i>{variant.name}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Please send your accounts, serial codes, or license keys as a message.\n\n"
        "⚠️ <b>Format:</b> Send multiple items separated by a new line:\n"
        "<code>item1_code_here\nitem2_code_here\nitem3_code_here</code>\n\n"
        "<i>Send /cancel at any time to abort.</i>"
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(AdminStockStates.waiting_for_stock_items)
async def handle_admin_stock_input(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Stock upload cancelled.")
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    variant_id = data.get("variant_id")
    variant_name = data.get("variant_name", "Product")

    if not product_id or not variant_id:
        await state.clear()
        await message.answer("Session expired. Please re-open /admin.")
        return

    lines = message.text.split("\n") if message.text else []
    inv_repo = InventoryRepository(session)
    count_added = await inv_repo.bulk_add_stock(product_id=product_id, variant_id=variant_id, payloads=lines)
    await session.commit()

    prod_repo = ProductRepository(session)
    total_stock = await prod_repo.get_variant_stock_count(variant_id)
    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 View Variant", callback_data=f"adm_var_{variant_id}")],
            [InlineKeyboardButton(text="⬅️ Back to Products", callback_data="admin_products")],
        ]
    )

    await message.answer(
        f"✅ <b>Successfully restocked {count_added} items!</b>\n\n"
        f"📦 Product: <b>{variant_name}</b>\n"
        f"📊 Total Available Stock: <code>{total_stock} items</code>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_edit_price_"))
async def handle_adm_edit_price_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    variant_id = int(callback.data.split("adm_edit_price_")[1])
    prod_repo = ProductRepository(session)
    variant = await prod_repo.get_variant_by_id(variant_id)

    if not variant:
        await callback.answer("Variant not found.", show_alert=True)
        return

    await state.set_state(AdminPriceStates.waiting_for_new_price)
    await state.update_data(variant_id=variant.id, current_price=str(variant.price), variant_name=f"{variant.product.name} ({variant.name})")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"adm_var_{variant.id}")],
        ]
    )

    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"✏️ <b>Edit Price for {variant.product.name}</b>\n"
            f"Current Price: <code>${variant.price:.2f}</code>\n\n"
            "Please send the new price in USD (e.g. <code>1.49</code>):",
            reply_markup=kb,
            parse_mode="HTML",
        )


@router.message(AdminPriceStates.waiting_for_new_price)
async def handle_admin_price_input(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Price edit cancelled.")
        return

    data = await state.get_data()
    variant_id = data.get("variant_id")

    try:
        new_price = Decimal(message.text.strip().replace("$", ""))
        if new_price < Decimal("0.01"):
            raise ValueError("Price must be at least $0.01")
    except Exception:
        await message.answer("⚠️ Invalid price format. Please enter a number like <code>1.99</code> or /cancel:")
        return

    prod_repo = ProductRepository(session)
    await prod_repo.update_variant_price(variant_id, new_price)
    await session.commit()
    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 View Variant", callback_data=f"adm_var_{variant_id}")],
            [InlineKeyboardButton(text="⬅️ Back to Products", callback_data="admin_products")],
        ]
    )

    await message.answer(
        f"✅ <b>Price updated to ${new_price:.2f}!</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_del_prod_"))
async def handle_adm_del_prod_confirm(callback: CallbackQuery, session: AsyncSession):
    product_id = int(callback.data.split("adm_del_prod_")[1])
    prod_repo = ProductRepository(session)
    product = await prod_repo.get_product_by_id(product_id)

    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Yes, Delete Permanently", callback_data=f"adm_confirm_del_{product.id}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_products")],
        ]
    )

    text = (
        f"⚠️ <b>Delete Confirmation</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Are you sure you want to permanently delete <b>{product.name}</b>?\n\n"
        "This will permanently delete the product, all variants, and any unsold stock items."
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_confirm_del_"))
async def handle_adm_del_prod_execute(callback: CallbackQuery, session: AsyncSession):
    product_id = int(callback.data.split("adm_confirm_del_")[1])
    prod_repo = ProductRepository(session)
    await prod_repo.delete_product(product_id)
    await session.commit()

    await callback.answer("🗑️ Product deleted!", show_alert=True)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Products", callback_data="admin_products")]
        ]
    )
    if callback.message:
        await callback.message.edit_text("✅ <b>Product has been deleted successfully.</b>", reply_markup=kb, parse_mode="HTML")
