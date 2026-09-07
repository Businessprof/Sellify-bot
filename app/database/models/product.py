from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DeliveryType
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.inventory import InventoryItem


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="📦", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan", order_by="Product.name"
    )


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    delivery_type: Mapped[DeliveryType] = mapped_column(
        Enum(DeliveryType), default=DeliveryType.AUTO_SERIAL, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    is_trial_or_email: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    # Relationships
    category: Mapped["ProductCategory"] = relationship("ProductCategory", back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.display_order"
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "18 Month Access"
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="variant", cascade="all, delete-orphan"
    )
