import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
from lib.database import db_manager
from lib.config import settings

logger = structlog.get_logger()


class AuthManager:
    def __init__(self):
        self.api_key_prefix = "vibe"
        self.api_key_length = 32
    
    def generate_api_key(self, environment: str = "prod") -> tuple[str, str]:
        """Generate a new API key and its hash"""
        # Generate random key
        random_part = secrets.token_urlsafe(self.api_key_length)[:self.api_key_length]
        api_key = f"{self.api_key_prefix}_{environment}_{random_part}"
        
        # Create hash for storage
        key_hash = self._hash_api_key(api_key)
        
        return api_key, key_hash
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage"""
        salted_key = f"{api_key}{settings.api_key_salt}"
        return hashlib.sha256(salted_key.encode()).hexdigest()
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return user information"""
        if not api_key or not api_key.startswith(self.api_key_prefix):
            return None
        
        key_hash = self._hash_api_key(api_key)
        pool = await db_manager.get_master_pool()
        
        async with pool.acquire() as conn:
            # Get user info from API key
            row = await conn.fetchrow(
                """
                SELECT 
                    k.id as key_id,
                    k.user_id,
                    k.expires_at,
                    u.email,
                    u.organization,
                    u.is_active as user_active,
                    k.is_active as key_active
                FROM api_keys k
                JOIN users u ON k.user_id = u.id
                WHERE k.key_hash = $1
                """,
                key_hash
            )
            
            if not row:
                await logger.ainfo("api_key_not_found", key_prefix=api_key[:15])
                return None
            
            # Check if key is active and not expired
            if not row['key_active'] or not row['user_active']:
                await logger.ainfo("api_key_inactive", user_id=str(row['user_id']))
                return None
            
            if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                await logger.ainfo("api_key_expired", user_id=str(row['user_id']))
                return None
            
            # Update last used timestamp
            await conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1",
                row['key_id']
            )
            
            return {
                'user_id': str(row['user_id']),
                'key_id': str(row['key_id']),
                'email': row['email'],
                'organization': row['organization']
            }
    
    async def create_api_key(
        self, 
        user_id: str, 
        name: str,
        environment: str = "prod",
        expires_in_days: Optional[int] = None
    ) -> str:
        """Create a new API key for a user"""
        api_key, key_hash = self.generate_api_key(environment)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_keys 
                (user_id, key_hash, key_prefix, name, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, key_hash, f"{self.api_key_prefix}_{environment}", 
                name, expires_at
            )
        
        await logger.ainfo("api_key_created", user_id=user_id, name=name)
        return api_key
    
    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key"""
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE api_keys 
                SET is_active = false 
                WHERE id = $1 AND user_id = $2
                """,
                key_id, user_id
            )
            
            if result == "UPDATE 1":
                await logger.ainfo("api_key_revoked", key_id=key_id, user_id=user_id)
                return True
            return False


# Singleton instance
auth_manager = AuthManager()