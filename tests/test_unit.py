"""
Unit tests for hashing service.
"""
import pytest
from app.services.hashing import generate_api_key, hash_api_key, verify_api_key


class TestHashing:
    """Tests for API key hashing."""
    
    def test_generate_api_key_returns_tuple(self):
        """Test that generate_api_key returns raw_key, hash, prefix."""
        raw_key, key_hash, key_prefix = generate_api_key()
        
        assert raw_key is not None
        assert key_hash is not None
        assert key_prefix is not None
        
    def test_generate_api_key_has_prefix(self):
        """Test that generated key has correct prefix."""
        raw_key, _, key_prefix = generate_api_key()
        
        assert raw_key.startswith("sk_live_")
        assert key_prefix.startswith("sk_live_")
        assert key_prefix.endswith("...")
        
    def test_generate_api_key_unique(self):
        """Test that each generated key is unique."""
        keys = [generate_api_key()[0] for _ in range(10)]
        assert len(set(keys)) == 10
        
    def test_hash_api_key_deterministic(self):
        """Test that hashing is deterministic."""
        raw_key = "sk_live_test123"
        hash1 = hash_api_key(raw_key)
        hash2 = hash_api_key(raw_key)
        
        assert hash1 == hash2
        
    def test_hash_api_key_different_for_different_keys(self):
        """Test that different keys produce different hashes."""
        hash1 = hash_api_key("sk_live_key1")
        hash2 = hash_api_key("sk_live_key2")
        
        assert hash1 != hash2
        
    def test_verify_api_key_valid(self):
        """Test verification of valid key."""
        raw_key, key_hash, _ = generate_api_key()
        
        assert verify_api_key(raw_key, key_hash) is True
        
    def test_verify_api_key_invalid(self):
        """Test verification of invalid key."""
        raw_key, key_hash, _ = generate_api_key()
        
        assert verify_api_key("sk_live_wrong", key_hash) is False


class TestIPUtils:
    """Tests for IP utilities."""
    
    def test_ip_allowed_no_whitelist(self):
        """Test that all IPs allowed when no whitelist."""
        from app.utils.ip_utils import is_ip_allowed
        
        assert is_ip_allowed("192.168.1.1", None) is True
        assert is_ip_allowed("192.168.1.1", []) is True
        
    def test_ip_allowed_exact_match(self):
        """Test exact IP matching."""
        from app.utils.ip_utils import is_ip_allowed
        
        whitelist = ["192.168.1.1", "10.0.0.1"]
        
        assert is_ip_allowed("192.168.1.1", whitelist) is True
        assert is_ip_allowed("10.0.0.1", whitelist) is True
        assert is_ip_allowed("172.16.0.1", whitelist) is False
        
    def test_ip_allowed_cidr(self):
        """Test CIDR notation matching."""
        from app.utils.ip_utils import is_ip_allowed
        
        whitelist = ["192.168.1.0/24"]
        
        assert is_ip_allowed("192.168.1.1", whitelist) is True
        assert is_ip_allowed("192.168.1.255", whitelist) is True
        assert is_ip_allowed("192.168.2.1", whitelist) is False
