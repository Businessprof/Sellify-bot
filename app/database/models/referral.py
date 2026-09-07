import uuid
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RewardType
from app.database.base import Base, TimestampMixin


class Referral(Base, TimestampMixin):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    referee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"), nullable=False)
    total_commission_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)


class ReferralTransaction(Base, TimestampMixin):
    __tablename__ = "referral_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    referee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PAID", nullable=False)


class ReferralReward(Base, TimestampMixin):
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    required_referrals: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[RewardType] = mapped_column(Enum(RewardType), nullable=False)
    reward_value: Mapped[str] = mapped_column(String(255), nullable=False)  # Balance amount or variant ID
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)


class ReferralRedemption(Base, TimestampMixin):
    __tablename__ = "referral_redemptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    reward_id: Mapped[int] = mapped_column(Integer, ForeignKey("referral_rewards.id"), index=True, nullable=False)
