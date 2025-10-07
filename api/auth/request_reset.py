"""
Password Reset Request API
Generates reset token and sends email to user
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
import secrets
import hashlib
from datetime import datetime, timedelta
import structlog
from lib.config import settings
from lib.database import db_manager
from lib.email_service import email_service

logger = structlog.get_logger()
router = APIRouter()


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    success: bool
    message: str


@router.post("/request-password-reset", response_model=PasswordResetResponse)
async def request_password_reset(request_data: PasswordResetRequest, request: Request):
    """
    Request a password reset email

    - Generates a secure reset token
    - Sends email with reset link
    - Always returns success (prevents email enumeration)
    """
    try:
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            # Find user by email
            user = await conn.fetchrow(
                """
                SELECT id, email, is_active
                FROM users
                WHERE email = $1
                """,
                request_data.email,
            )

            # Always return success to prevent email enumeration
            if not user:
                await logger.ainfo("password_reset_request_unknown_email", email=request_data.email)
                return PasswordResetResponse(
                    success=True,
                    message="If an account exists with that email, a reset link has been sent.",
                )

            if not user["is_active"]:
                await logger.awarning(
                    "password_reset_request_inactive_user",
                    user_id=str(user["id"]),
                    email=request_data.email,
                )
                return PasswordResetResponse(
                    success=True,
                    message="If an account exists with that email, a reset link has been sent.",
                )

            # Generate secure reset token (32 bytes = 256 bits)
            reset_token = secrets.token_urlsafe(32)

            # Hash the token for storage (SHA-256)
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(
                hours=settings.password_reset_token_expiry_hours
            )

            # Get request metadata
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")

            # Store hashed token in database
            await conn.execute(
                """
                INSERT INTO password_reset_tokens
                (user_id, token_hash, email, expires_at, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user["id"],
                token_hash,
                user["email"],
                expires_at,
                ip_address,
                user_agent,
            )

            # Send reset email
            email_sent = await email_service.send_password_reset_email(
                to_email=user["email"],
                reset_token=reset_token,  # Send actual token in email, not hash
                user_id=str(user["id"]),
            )

            if email_sent:
                await logger.ainfo(
                    "password_reset_email_sent",
                    user_id=str(user["id"]),
                    email=user["email"],
                    expires_at=expires_at.isoformat(),
                )
            else:
                await logger.aerror(
                    "password_reset_email_failed",
                    user_id=str(user["id"]),
                    email=user["email"],
                )

            return PasswordResetResponse(
                success=True,
                message="If an account exists with that email, a reset link has been sent.",
            )

    except Exception as e:
        await logger.aerror("password_reset_request_error", error=str(e), email=request_data.email)
        # Don't expose internal errors
        return PasswordResetResponse(
            success=True,
            message="If an account exists with that email, a reset link has been sent.",
        )


app = router
