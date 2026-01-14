"""
Secure API key generation and hashing.

SECURITY CRITICAL:
- Raw keys are NEVER stored in database
- Keys are hashed using HMAC-SHA256
- Constant-time comparison prevents timing attacks
"""
import secrets
import hashlib
import hmac
from app.config import settings


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    
    Returns:
        tuple: (raw_key, key_hash, key_prefix)
        
    raw_key is returned ONCE and should be shown to user immediately.
    Only key_hash and key_prefix are stored in database.
    """
    # Generate 32 random bytes (256 bits of entropy)
    random_bytes = secrets.token_urlsafe(32)
    
    # Create full key with prefix
    raw_key = f"{settings.API_KEY_PREFIX}{random_bytes}"
    
    # Create hash for storage
    key_hash = hash_api_key(raw_key)
    
    # Create prefix for identification (first 12 chars after prefix)
    key_prefix = raw_key[:len(settings.API_KEY_PREFIX) + 8] + "..."
    
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """
    Hash an API key using HMAC-SHA256.
    
    Args:
        raw_key: The raw API key to hash
        
    Returns:
        str: Hexadecimal hash of the key
    """
    return hmac.new(
        key=settings.SECRET_KEY.encode(),
        msg=raw_key.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        raw_key: The raw API key from request
        stored_hash: The hash stored in database
        
    Returns:
        bool: True if key matches, False otherwise
    """
    computed_hash = hash_api_key(raw_key)
    return hmac.compare_digest(computed_hash, stored_hash)
