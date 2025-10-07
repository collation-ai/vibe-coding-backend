"""
Password Expiry Background Job
Sends warning emails to users with expiring passwords
"""
import asyncio
from datetime import datetime
import structlog
from lib.database import db_manager
from lib.email_service import email_service
from lib.config import settings

logger = structlog.get_logger()


async def check_expiring_passwords():
    """
    Check for expiring passwords and send warning emails

    Sends emails at:
    - 14 days before expiry
    - 7 days before expiry
    - 3 days before expiry
    - 1 day before expiry
    """
    try:
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            # Get users with expiring passwords (next 14 days)
            users = await conn.fetch(
                """
                SELECT * FROM get_users_with_expiring_passwords(14)
                """
            )

            for user in users:
                days_until_expiry = user['days_until_expiry']

                # Send warning at specific intervals
                should_send = days_until_expiry in [14, 7, 3, 1]

                if should_send:
                    # Check if we've already sent a warning for this day
                    last_warning = await conn.fetchrow(
                        """
                        SELECT id, created_at
                        FROM email_notifications
                        WHERE user_id = $1
                        AND email_type = 'password_expiry_warning'
                        AND created_at >= NOW() - INTERVAL '1 day'
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        user['user_id']
                    )

                    if not last_warning:
                        # Send warning email
                        await email_service.send_password_expiry_warning(
                            to_email=user['email'],
                            user_id=str(user['user_id']),
                            days_until_expiry=days_until_expiry
                        )

                        await logger.ainfo(
                            "password_expiry_warning_sent",
                            user_id=str(user['user_id']),
                            email=user['email'],
                            days_until_expiry=days_until_expiry
                        )

            # Handle expired passwords
            expired_users = await conn.fetch(
                """
                SELECT id, email, password_expires_at
                FROM users
                WHERE is_active = true
                AND password_expires_at < NOW()
                AND password_reset_required = false
                """
            )

            for user in expired_users:
                # Mark password reset as required
                await conn.execute(
                    """
                    UPDATE users
                    SET password_reset_required = true,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    user['id']
                )

                await logger.ainfo(
                    "password_expired_reset_required",
                    user_id=str(user['id']),
                    email=user['email'],
                    expired_at=user['password_expires_at'].isoformat()
                )

            await logger.ainfo(
                "password_expiry_check_complete",
                users_with_expiring_passwords=len(users),
                users_with_expired_passwords=len(expired_users)
            )

    except Exception as e:
        await logger.aerror(
            "password_expiry_check_error",
            error=str(e)
        )


async def run_password_expiry_job():
    """
    Run the password expiry job continuously
    Checks every 6 hours
    """
    while True:
        await check_expiring_passwords()
        # Wait 6 hours before next check
        await asyncio.sleep(6 * 60 * 60)


if __name__ == "__main__":
    # For testing: run once
    asyncio.run(check_expiring_passwords())
