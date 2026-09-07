from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import logger
from app.database.models.user import MembershipChannel


class MembershipService:
    ALLOWED_STATUSES = {"creator", "administrator", "member", "restricted"}

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    async def get_required_channels(self) -> list[dict]:
        """Fetch all mandatory channels/groups from database or fallback to settings."""
        if self.session:
            query = select(MembershipChannel).where(
                MembershipChannel.is_mandatory == True,  # noqa: E712
                MembershipChannel.is_active == True,     # noqa: E712
            )
            res = await self.session.execute(query)
            channels = list(res.scalars().all())
            if channels:
                return [
                    {
                        "id": ch.channel_id,
                        "title": ch.title,
                        "link": ch.invite_link,
                    }
                    for ch in channels
                ]

        # Fallback to configured settings
        return [
            {
                "id": settings.MANDATORY_CHANNEL_ID,
                "title": "Join Channel",
                "link": settings.MANDATORY_CHANNEL_LINK,
            },
            {
                "id": settings.MANDATORY_GROUP_ID,
                "title": "Join Group",
                "link": settings.MANDATORY_GROUP_LINK,
            },
        ]

    async def verify_user_membership(self, bot: Bot, user_id: int) -> tuple[bool, list[dict]]:
        """
        Verify that a user is an active member of all mandatory channels/groups.
        Returns (is_verified, missing_channels).
        """
        required = await self.get_required_channels()
        missing = []

        for ch in required:
            try:
                member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
                if member.status not in self.ALLOWED_STATUSES:
                    missing.append(ch)
            except Exception as e:
                logger.warning(
                    f"Could not verify membership for user {user_id} in {ch['id']}: {e}. Treating as unverified."
                )
                missing.append(ch)

        is_verified = len(missing) == 0
        return is_verified, missing
