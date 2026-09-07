import hashlib
import secrets
import string


def generate_referral_code(prefix: str = "REF", length: int = 8) -> str:
    """Generate a high-entropy alphanumeric referral code (e.g. REF43F3E22A)."""
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{suffix}"


def generate_api_key(prefix: str = "qam_live_") -> tuple[str, str, str]:
    """
    Generate a reseller API key.
    Returns: (raw_key, key_prefix, key_hash)
    Only raw_key is shown to the user once. key_hash is stored in DB.
    """
    random_bytes = secrets.token_urlsafe(32)
    raw_key = f"{prefix}{random_bytes}"
    key_prefix = raw_key[:16]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_prefix, key_hash


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of hashed API key."""
    computed_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed_hash, stored_hash)
