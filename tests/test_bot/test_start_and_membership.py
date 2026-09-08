from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import ChatMemberMember, ChatMemberLeft
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import format_welcome_message
from app.bot.keyboards.menu import get_main_menu_keyboard, get_membership_gate_keyboard
from app.core.constants import MembershipTier, UserRole
from app.database.models.user import User
from app.services.membership_service import MembershipService


def test_format_welcome_message():
    user = User(
        id=6186806738,
        first_name="White Angel",
        username="Cadavasi",
        membership_tier=MembershipTier.BRONZE,
        role=UserRole.USER,
        referral_code="REF43F3E22A",
    )
    text = format_welcome_message(
        user=user,
        balance=Decimal("0.00"),
        total_spent=Decimal("0.00"),
        referral_count=0,
        referral_earnings=Decimal("0.00"),
        referral_link="https://t.me/digiproductsllr_bot?start=ref_REF43F3E22A",
    )

    assert "🆂 🅴 🅻 🅻 🅸 🅵 🆈" in text
    assert "White Angel" in text
    assert "@Cadavasi" in text
    assert "6186806738" in text
    assert "🥉 Bronze" in text
    assert "$0.00" in text
    assert "https://t.me/digiproductsllr_bot?start=ref_REF43F3E22A" in text


def test_membership_gate_keyboard():
    channels = [
        {"title": "Join Channel", "link": "https://t.me/sellify_announcement"},
        {"title": "Join Group", "link": "https://t.me/+SpKs2_u6NcxiN2M1"},
    ]
    kb = get_membership_gate_keyboard(channels)
    assert len(kb.inline_keyboard) == 3
    assert kb.inline_keyboard[0][0].text == "📢 Join Channel"
    assert kb.inline_keyboard[0][0].url == "https://t.me/sellify_announcement"
    assert kb.inline_keyboard[1][0].text == "📢 Join Group"
    assert kb.inline_keyboard[2][0].text == "✅ I have joined"
    assert kb.inline_keyboard[2][0].callback_data == "verify_membership"


def test_main_menu_keyboard_layout():
    kb = get_main_menu_keyboard()
    assert len(kb.inline_keyboard) == 5

    # Row 1: SHOP
    assert len(kb.inline_keyboard[0]) == 1
    assert "SHOP" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[0][0].callback_data == "nav_shop"

    # Row 2: Wallet | Freebies | Profile
    assert len(kb.inline_keyboard[1]) == 3
    assert "Wallet" in kb.inline_keyboard[1][0].text
    assert "Freebies" in kb.inline_keyboard[1][1].text
    assert "Profile" in kb.inline_keyboard[1][2].text

    # Row 3: Referral Store
    assert len(kb.inline_keyboard[2]) == 1
    assert "Referral Store" in kb.inline_keyboard[2][0].text

    # Row 4: Support | Emails & Trials
    assert len(kb.inline_keyboard[3]) == 2
    assert "Support" in kb.inline_keyboard[3][0].text
    assert "Emails & Trials" in kb.inline_keyboard[3][1].text

    # Row 5: Reseller API | Clear Chat
    assert len(kb.inline_keyboard[4]) == 2
    assert "Reseller API" in kb.inline_keyboard[4][0].text
    assert "Clear Chat" in kb.inline_keyboard[4][1].text


@pytest.mark.asyncio
async def test_membership_service_verification_flow(db_session: AsyncSession):
    service = MembershipService(db_session)
    mock_bot = MagicMock()

    # Case 1: Member has joined all
    mock_member = MagicMock(spec=ChatMemberMember)
    mock_member.status = "member"
    mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

    is_verified, missing = await service.verify_user_membership(mock_bot, 123456)
    assert is_verified is True
    assert len(missing) == 0

    # Case 2: Member has not joined
    mock_left = MagicMock(spec=ChatMemberLeft)
    mock_left.status = "left"
    mock_bot.get_chat_member = AsyncMock(return_value=mock_left)

    is_verified, missing = await service.verify_user_membership(mock_bot, 123456)
    assert is_verified is False
    assert len(missing) > 0
