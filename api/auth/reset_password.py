"""
Password Reset API
Verifies token and resets user password
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
import hashlib
from datetime import datetime
import structlog
from lib.database import db_manager
from lib.auth import hash_password

logger = structlog.get_logger()
router = APIRouter()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request_data: ResetPasswordRequest):
    """
    Reset password using valid reset token

    - Verifies token is valid and not expired
    - Checks token hasn't been used
    - Updates password and marks token as used
    - Stores old password in history
    """
    try:
        # Hash the provided token to match against stored hash
        token_hash = hashlib.sha256(request_data.token.encode()).hexdigest()

        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            # Find valid token
            token_record = await conn.fetchrow(
                """
                SELECT id, user_id, email, expires_at, used_at
                FROM password_reset_tokens
                WHERE token_hash = $1
                """,
                token_hash,
            )

            if not token_record:
                await logger.awarning(
                    "password_reset_invalid_token",
                    token_hash=token_hash[:16] + "...",  # Log partial hash
                )
                raise HTTPException(
                    status_code=400, detail="Invalid or expired reset token"
                )

            # Check if token already used
            if token_record["used_at"]:
                await logger.awarning(
                    "password_reset_token_reuse_attempt",
                    user_id=str(token_record["user_id"]),
                    used_at=token_record["used_at"].isoformat(),
                )
                raise HTTPException(
                    status_code=400, detail="This reset token has already been used"
                )

            # Check if token expired
            if datetime.utcnow() > token_record["expires_at"]:
                await logger.awarning(
                    "password_reset_token_expired",
                    user_id=str(token_record["user_id"]),
                    expired_at=token_record["expires_at"].isoformat(),
                )
                raise HTTPException(
                    status_code=400,
                    detail="Reset token has expired. Please request a new one.",
                )

            # Get user's current password for history
            user = await conn.fetchrow(
                """
                SELECT id, password_hash, is_active
                FROM users
                WHERE id = $1
                """,
                token_record["user_id"],
            )

            if not user or not user["is_active"]:
                raise HTTPException(
                    status_code=400, detail="User account not found or inactive"
                )

            # Check if new password matches current password
            if user["password_hash"] == hash_password(request_data.new_password):
                raise HTTPException(
                    status_code=400,
                    detail="New password cannot be the same as current password",
                )

            # Check password history (prevent reuse of last 5 passwords)
            password_history = await conn.fetch(
                """
                SELECT password_hash
                FROM password_history
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                user["id"],
            )

            new_password_hash = hash_password(request_data.new_password)
            for old_password in password_history:
                if old_password["password_hash"] == new_password_hash:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot reuse a recent password. Please choose a different one.",
                    )

            # Start transaction for password update
            async with conn.transaction():
                # Store old password in history
                await conn.execute(
                    """
                    INSERT INTO password_history (user_id, password_hash)
                    VALUES ($1, $2)
                    """,
                    user["id"],
                    user["password_hash"],
                )

                # Update user's password
                await conn.execute(
                    """
                    UPDATE users
                    SET password_hash = $1,
                        password_changed_at = NOW(),
                        password_expires_at = NOW() + INTERVAL '90 days',
                        password_reset_required = false,
                        failed_login_attempts = 0,
                        locked_until = NULL,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    new_password_hash,
                    user["id"],
                )

                # Mark token as used
                await conn.execute(
                    """
                    UPDATE password_reset_tokens
                    SET used_at = NOW()
                    WHERE id = $1
                    """,
                    token_record["id"],
                )

            await logger.ainfo(
                "password_reset_successful",
                user_id=str(user["id"]),
                email=token_record["email"],
            )

            return ResetPasswordResponse(
                success=True, message="Password has been reset successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror("password_reset_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to reset password. Please try again."
        )


app = router
