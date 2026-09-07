from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import MembershipTier, UserRole
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.wallet import Wallet
    from app.database.models.order import Order
    from app.database.models.support import SupportTicket


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("id != referred_by_id", name="check_cannot_refer_self"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram User ID
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    membership_tier: Mapped[MembershipTier] = mapped_column(
        Enum(MembershipTier), default=MembershipTier.BRONZE, nullable=False
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    referral_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    tickets: Mapped[list["SupportTicket"]] = relationship("SupportTicket", back_populates="user")
    referrer: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[referred_by_id],
        back_populates="referred_users",
    )
    referred_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[referred_by_id],
        back_populates="referrer",
    )


class MembershipChannel(Base, TimestampMixin):
    __tablename__ = "membership_channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    invite_link: Mapped[str] = mapped_column(String(255), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
