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
            # Skip checking dummy/placeholder IDs
            if ch["id"] in (-1001987654321, -1001234567890):
                logger.warning(
                    f"Channel/Group '{ch['title']}' has placeholder ID {ch['id']}. Skipping membership check."
                )
                continue

            try:
                member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
                if member.status not in self.ALLOWED_STATUSES:
                    ch_info = dict(ch)
                    ch_info["reason"] = "not_joined"
                    ch_info["detail"] = f"Join {ch['title']}"
                    missing.append(ch_info)
            except Exception as e:
                err_str = str(e)
                logger.warning(
                    f"Could not verify membership for user {user_id} in {ch['id']}: {e}."
                )
                ch_info = dict(ch)
                if "member list is inaccessible" in err_str or "not a member" in err_str.lower() or "forbidden" in err_str.lower():
                    ch_info["reason"] = "bot_not_admin"
                    ch_info["detail"] = f"Bot is not an Admin in '{ch['title']}'"
                elif "chat not found" in err_str:
                    ch_info["reason"] = "chat_not_found"
                    ch_info["detail"] = f"Chat '{ch['title']}' not found"
                else:
                    ch_info["reason"] = "error"
                    ch_info["detail"] = err_str
                missing.append(ch_info)

        is_verified = len(missing) == 0
        return is_verified, missing
