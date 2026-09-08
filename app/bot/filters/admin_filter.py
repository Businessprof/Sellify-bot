from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User as TgUser

from app.core.config import settings
from app.core.constants import UserRole
from app.database.models.user import User


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject, db_user: User | None = None, event_from_user: TgUser | None = None) -> bool:
        user_id = event_from_user.id if event_from_user else None
        if not user_id:
            return False

        # Check configured admin IDs
        if user_id in settings.ADMIN_TELEGRAM_IDS:
            return True

        # Check database role
        if db_user and db_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return True

        return False
