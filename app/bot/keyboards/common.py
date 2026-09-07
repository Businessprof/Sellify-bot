from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_keyboard(callback_data: str = "nav_main_menu") -> InlineKeyboardMarkup:
    """Standard back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data=callback_data)],
        ]
    )
