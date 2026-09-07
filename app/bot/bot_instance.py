from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import menu_router, start_router
from app.bot.middlewares.db_session import DatabaseSessionMiddleware
from app.bot.middlewares.user_tracker import UserTrackerMiddleware
from app.core.config import settings


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Outer middleware runs before filters and handlers
    dp.update.outer_middleware(DatabaseSessionMiddleware())

    # User tracker runs on incoming messages and callback queries
    user_tracker = UserTrackerMiddleware()
    dp.message.middleware(user_tracker)
    dp.callback_query.middleware(user_tracker)

    # Register routers
    dp.include_router(start_router)
    dp.include_router(menu_router)

    return dp
