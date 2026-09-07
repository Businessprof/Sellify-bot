from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.logger import logger


def mask_username(name: str | None) -> str:
    """Anonymizes user names for public broadcasts (e.g., 'User J*****')."""
    if not name:
        return "User A*****"
    cleaned = name.replace("@", "").strip()
    if len(cleaned) <= 1:
        return f"User {cleaned}*****"
    return f"User {cleaned[0]}*****"


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def broadcast_live_purchase(
        self,
        customer_name: str | None,
        product_name: str,
        quantity: int = 1,
        variant_id: int | None = None,
    ) -> None:
        """
        Broadcasts live purchase announcements to community group/channel
        matching Screenshot 2 format:
        'User J***** just bought 1x 🇬 Gemini AI Pro 18 Month!'
        with attached button linking directly to the product.
        """
        target_chat_id = settings.LIVE_SALES_CHANNEL_ID or settings.MANDATORY_GROUP_ID
        if not target_chat_id:
            return

        masked = mask_username(customer_name)
        text = f"<b>{masked}</b> just bought {quantity}× <b>{product_name}</b>! 🎉"

        reply_markup = None
        if variant_id:
            bot_username = settings.BOT_USERNAME
            deep_link = f"https://t.me/{bot_username}?start=buy_{variant_id}"
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"🛒 {product_name} ↗", url=deep_link)]
                ]
            )

        try:
            await self.bot.send_message(
                chat_id=target_chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not broadcast live purchase to chat {target_chat_id}: {e}")

    async def broadcast_freebie_claim(
        self,
        customer_name: str | None,
        reward_name: str,
    ) -> None:
        """
        Broadcasts freebie claim:
        'User T***** just claimed free 🎁 Surfshark VPN Premium.'
        """
        target_chat_id = settings.LIVE_SALES_CHANNEL_ID or settings.MANDATORY_GROUP_ID
        if not target_chat_id:
            return

        masked = mask_username(customer_name)
        text = f"<b>{masked}</b> just claimed free 🎁 <b>{reward_name}</b>!"

        try:
            await self.bot.send_message(
                chat_id=target_chat_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not broadcast freebie claim: {e}")
