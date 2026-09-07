from enum import Enum


class MembershipTier(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    DIAMOND = "DIAMOND"

    @property
    def badge(self) -> str:
        badges = {
            self.BRONZE: "🥉 Bronze",
            self.SILVER: "🥈 Silver",
            self.GOLD: "🥇 Gold",
            self.DIAMOND: "💎 Diamond",
        }
        return badges.get(self, "🥉 Bronze")


class UserRole(str, Enum):
    USER = "USER"
    SUPPORT = "SUPPORT"
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class PaymentMethod(str, Enum):
    WALLET = "WALLET"
    TELEGRAM_STARS = "TELEGRAM_STARS"
    CRYPTO = "CRYPTO"
    EXTERNAL_GATEWAY = "EXTERNAL_GATEWAY"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    ORDER_PAYMENT = "ORDER_PAYMENT"
    ORDER_REFUND = "ORDER_REFUND"
    REFERRAL_BONUS = "REFERRAL_BONUS"
    FREEBIE_BONUS = "FREEBIE_BONUS"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"


class InventoryStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class DeliveryType(str, Enum):
    AUTO_SERIAL = "AUTO_SERIAL"
    AUTO_ACCOUNT = "AUTO_ACCOUNT"
    LICENSE_KEY = "LICENSE_KEY"
    MANUAL = "MANUAL"


class SupportCategory(str, Enum):
    PAYMENT = "PAYMENT"
    ORDER = "ORDER"
    ACCOUNT = "ACCOUNT"
    OTHER = "OTHER"

    @property
    def label(self) -> str:
        labels = {
            self.PAYMENT: "💳 Payment Problem",
            self.ORDER: "📦 Order Problem",
            self.ACCOUNT: "🔐 Account Problem",
            self.OTHER: "❓ Other Issue",
        }
        return labels.get(self, "❓ Other Issue")


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class RewardType(str, Enum):
    WALLET_CREDIT = "WALLET_CREDIT"
    PRODUCT_VARIANT = "PRODUCT_VARIANT"
    COUPON = "COUPON"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"
