import pytest
import asyncio
from lib.auth import auth_manager
from lib.database import db_manager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_generate_api_key():
    """Test API key generation"""
    api_key, key_hash = auth_manager.generate_api_key("test")
    
    assert api_key.startswith("vibe_test_")
    assert len(api_key) == 42  # vibe_test_ (10) + 32 chars
    assert key_hash is not None
    assert len(key_hash) == 64  # SHA256 hash


@pytest.mark.asyncio
async def test_hash_api_key():
    """Test API key hashing is consistent"""
    api_key = "vibe_test_sample_key_12345"
    
    hash1 = auth_manager._hash_api_key(api_key)
    hash2 = auth_manager._hash_api_key(api_key)
    
    assert hash1 == hash2
    assert len(hash1) == 64


@pytest.mark.asyncio
async def test_validate_identifier():
    """Test identifier validation"""
    # Valid identifiers
    assert await db_manager.validate_identifier("users") == True
    assert await db_manager.validate_identifier("user_accounts") == True
    assert await db_manager.validate_identifier("table123") == True
    
    # Invalid identifiers
    assert await db_manager.validate_identifier("123table") == False
    assert await db_manager.validate_identifier("user-table") == False
    assert await db_manager.validate_identifier("table@name") == False
    assert await db_manager.validate_identifier("") == False
    assert await db_manager.validate_identifier("a" * 64) == False  # Too long