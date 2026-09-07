from collections.abc import Awaitable, Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser

from app.database.repositories.user_repo import UserRepository


class UserTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_user: TgUser | None = data.get("event_from_user")
        session = data.get("session")

        if event_user and session:
            user_repo = UserRepository(session)

            # Check if there is a deep link referral in a /start command
            referrer_code: str | None = None
            if isinstance(event, Message) and event.text and event.text.startswith("/start ref_"):
                parts = event.text.split("ref_", 1)
                if len(parts) > 1:
                    referrer_code = parts[1].strip()

            db_user, _ = await user_repo.get_or_create_user(
                telegram_id=event_user.id,
                first_name=event_user.first_name,
                username=event_user.username,
                last_name=event_user.last_name,
                referrer_code=referrer_code,
            )

            # If user is banned, drop or notify
            if db_user.is_banned:
                if isinstance(event, Message):
                    await event.answer("🚫 Your account is currently suspended. Please contact support.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Your account is suspended.", show_alert=True)
                return

            data["db_user"] = db_user

        return await handler(event, data)
