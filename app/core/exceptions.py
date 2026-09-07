class QamifyBaseException(Exception):
    """Base exception for all domain-specific errors."""
    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)


class InsufficientBalanceError(QamifyBaseException):
    """Raised when user wallet balance is lower than required amount."""
    def __init__(self, required: float, current: float):
        super().__init__(f"Insufficient balance. Required: {required:.2f}, Current: {current:.2f}")
        self.required = required
        self.current = current


class OutOfStockError(QamifyBaseException):
    """Raised when product variant has zero available inventory items."""
    def __init__(self, variant_name: str = "Requested item"):
        super().__init__(f"{variant_name} is currently out of stock.")
        self.variant_name = variant_name


class MembershipRequiredError(QamifyBaseException):
    """Raised when user has not joined mandatory channels or groups."""
    def __init__(self, missing_channels: list[str] | None = None):
        channels_str = ", ".join(missing_channels) if missing_channels else "required channels"
        super().__init__(f"Membership verification failed for: {channels_str}")
        self.missing_channels = missing_channels or []


class UserBannedError(QamifyBaseException):
    """Raised when banned user attempts to interact with the bot."""
    def __init__(self, reason: str = "Your account is suspended."):
        super().__init__(reason)
        self.reason = reason


class ReferralSelfError(QamifyBaseException):
    """Raised when user attempts to refer themselves."""
    def __init__(self):
        super().__init__("Self-referrals are prohibited.")


class ReferralAlreadyReferredError(QamifyBaseException):
    """Raised when user already has an attributed referrer."""
    def __init__(self):
        super().__init__("User is already registered with a referrer.")


class InvalidCouponError(QamifyBaseException):
    """Raised when coupon code is invalid, expired, or usage limit exceeded."""
    def __init__(self, reason: str = "Invalid or expired coupon code."):
        super().__init__(reason)


class FreebieCooldownError(QamifyBaseException):
    """Raised when user attempts to claim freebie during cooldown period."""
    def __init__(self, hours_remaining: float):
        super().__init__(f"Freebie on cooldown. Please retry in {hours_remaining:.1f} hours.")
        self.hours_remaining = hours_remaining
