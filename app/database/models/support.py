import uuid
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import SupportCategory, TicketStatus
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.user import User


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category: Mapped[SupportCategory] = mapped_column(
        Enum(SupportCategory), default=SupportCategory.OTHER, nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.OPEN, index=True, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at"
    )


class TicketMessage(Base, TimestampMixin):
    __tablename__ = "ticket_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)  # USER, ADMIN, SYSTEM
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")
