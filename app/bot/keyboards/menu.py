from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_membership_gate_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    """
    Builds the gate keyboard with URL buttons for joining channel/group
    and a verification callback button: [✅ I have joined]
    """
    buttons = []
    for ch in channels:
        title = ch.get("title", "📢 Join Channel")
        link = ch.get("link", "https://t.me")
        buttons.append([InlineKeyboardButton(text=f"📢 {title}", url=link)])

    buttons.append([InlineKeyboardButton(text="✅ I have joined", callback_data="verify_membership")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Reproduces the exact Qamify high-conversion inline keyboard grid:
    Row 1: [🛍️ SHOP]
    Row 2: [💳 Wallet] [🎁 Freebies] [🙂 Profile]
    Row 3: [🎯 Referral Store]
    Row 4: [🛟 Support] [📨 Emails & Trials ↗]
    Row 5: [Reseller API] [🧹 Clear Chat]
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🛍️ SHOP", callback_data="nav_shop"),
        ],
        [
            InlineKeyboardButton(text="💳 Wallet", callback_data="nav_wallet"),
            InlineKeyboardButton(text="🎁 Freebies", callback_data="nav_freebies"),
            InlineKeyboardButton(text="🙂 Profile", callback_data="nav_profile"),
        ],
        [
            InlineKeyboardButton(text="🎯 Referral Store", callback_data="nav_referral_store"),
        ],
        [
            InlineKeyboardButton(text="🛟 Support", callback_data="nav_support"),
            InlineKeyboardButton(text="📨 Emails & Trials ↗", callback_data="nav_trials"),
        ],
        [
            InlineKeyboardButton(text="Reseller API", callback_data="nav_reseller"),
            InlineKeyboardButton(text="🧹 Clear Chat", callback_data="nav_clear_chat"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
