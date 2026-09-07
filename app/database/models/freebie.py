import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RewardType
from app.database.base import Base, TimestampMixin


class Freebie(Base, TimestampMixin):
    __tablename__ = "freebies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reward_type: Mapped[RewardType] = mapped_column(Enum(RewardType), default=RewardType.WALLET_CREDIT, nullable=False)
    reward_value: Mapped[str] = mapped_column(String(255), nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)  # 24h default cooldown
    stock_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Nullable = unlimited
    claimed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FreebieClaim(Base, TimestampMixin):
    __tablename__ = "freebie_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    freebie_id: Mapped[int] = mapped_column(Integer, ForeignKey("freebies.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
