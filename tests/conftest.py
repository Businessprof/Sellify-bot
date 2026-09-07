import asyncio
from decimal import Decimal
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import MembershipTier, UserRole
from app.database.base import Base
from app.database.models import *  # noqa: F403
from app.database.models.user import MembershipChannel, User
from app.database.models.wallet import Wallet


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, in-memory SQLite database session for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample verified user with associated wallet."""
    user = User(
        id=6186806738,
        first_name="White Angel",
        username="Cadavasi",
        membership_tier=MembershipTier.BRONZE,
        role=UserRole.USER,
        referral_code="REF43F3E22A",
    )
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(
        user_id=user.id,
        balance=Decimal("100.00"),
        total_deposited=Decimal("100.00"),
        total_spent=Decimal("0.00"),
    )
    db_session.add(wallet)
    await db_session.flush()
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def sample_channel(db_session: AsyncSession) -> MembershipChannel:
    channel = MembershipChannel(
        title="Test Channel",
        channel_id=-100123456789,
        invite_link="https://t.me/test_channel",
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    return channel
