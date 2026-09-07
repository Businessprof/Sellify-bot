import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InventoryStatus
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.product import ProductVariant
    from app.database.models.order import Order


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"
    __table_args__ = (
        Index("idx_inventory_variant_status", "variant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    variant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # License key, account credentials, or access link
    status: Mapped[InventoryStatus] = mapped_column(
        Enum(InventoryStatus), default=InventoryStatus.AVAILABLE, index=True, nullable=False
    )
    order_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="inventory_items")
    order: Mapped["Order | None"] = relationship("Order", back_populates="inventory_items")
