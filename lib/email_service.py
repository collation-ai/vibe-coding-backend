"""
Email Service using Azure Communication Services
Handles sending emails for password resets, notifications, etc.
"""
from typing import Optional
import structlog
from lib.config import settings
from lib.database import db_manager

logger = structlog.get_logger()


class EmailService:
    """Sends emails via Azure Communication Services"""

    def __init__(self):
        self.conn_string = settings.azure_comm_service_conn_string
        self.sender_email = settings.azure_comm_sender_email
        self.sender_name = settings.azure_comm_sender_name
        self.enabled = bool(self.conn_string and self.sender_email)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        user_id: Optional[str] = None,
        email_type: str = "general",
    ) -> bool:
        """
        Send an email using Azure Communication Services

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            user_id: Optional user ID for logging
            email_type: Type of email (password_reset, etc.)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            await logger.awarning(
                "email_service_not_configured", to_email=to_email, subject=subject
            )
            # Log to database even if not sent
            await self._log_email(
                to_email=to_email,
                subject=subject,
                body=html_body,
                user_id=user_id,
                email_type=email_type,
                error_message="Email service not configured",
            )
            return False

        try:
            # Import Azure SDK only when needed
            from azure.communication.email import EmailClient

            client = EmailClient.from_connection_string(self.conn_string)

            message = {
                "senderAddress": self.sender_email,
                "recipients": {
                    "to": [{"address": to_email}],
                },
                "content": {
                    "subject": subject,
                    "html": html_body,
                },
            }

            poller = client.begin_send(message)
            result = poller.result()

            await logger.ainfo(
                "email_sent",
                to_email=to_email,
                subject=subject,
                message_id=result.get("id"),
                email_type=email_type,
            )

            # Log successful send
            await self._log_email(
                to_email=to_email,
                subject=subject,
                body=html_body,
                user_id=user_id,
                email_type=email_type,
                message_id=result.get("id"),
            )

            return True

        except Exception as e:
            await logger.aerror(
                "email_send_failed",
                to_email=to_email,
                subject=subject,
                error=str(e),
                email_type=email_type,
            )

            # Log failed send
            await self._log_email(
                to_email=to_email,
                subject=subject,
                body=html_body,
                user_id=user_id,
                email_type=email_type,
                error_message=str(e),
                failed=True,
            )

            return False

    async def _log_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        user_id: Optional[str],
        email_type: str,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        failed: bool = False,
    ):
        """Log email to database"""
        try:
            pool = await db_manager.get_master_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO email_notifications
                    (user_id, email_to, email_type, subject, body, sent_at,
                     failed_at, error_message, message_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    user_id,
                    to_email,
                    email_type,
                    subject,
                    body,
                    None if failed else "NOW()",
                    "NOW()" if failed else None,
                    error_message,
                    message_id,
                )
        except Exception as e:
            await logger.aerror("email_log_failed", error=str(e))

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_id: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Send password reset email

        Args:
            to_email: User's email address
            reset_token: Password reset token
            user_id: User ID
            user_name: Optional user name

        Returns:
            True if sent successfully
        """
        # Build reset URL (this would be the frontend URL in production)
        base_url = (
            settings.frontend_url if hasattr(settings, "frontend_url") else "http://localhost:8000"
        )
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        subject = "Password Reset Request - Vibe Coding"

        html_body = f"""  # noqa: E501
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello{' ' + user_name if user_name else ''},</p>

                    <p>We received a request to reset your password for your Vibe Coding account.</p>

                    <p>Click the button below to reset your password:</p>

                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #fff; padding: 10px; border-radius: 5px;">
                        {reset_url}
                    </p>

                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link expires in {settings.password_reset_token_expiry_hours} hours</li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Never share this link with anyone</li>
                        </ul>
                    </div>

                    <p>If you're having trouble, contact our support team.</p>

                    <p>Best regards,<br>
                    <strong>Vibe Coding Team</strong></p>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply to this message.</p>
                    <p>&copy; 2025 Vibe Coding. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            user_id=user_id,
            email_type="password_reset",
        )

    async def send_password_expiry_warning(
        self,
        to_email: str,
        user_id: str,
        days_until_expiry: int,
        user_name: Optional[str] = None,
    ) -> bool:
        """Send password expiry warning email"""
        subject = f"⚠️ Your password expires in {days_until_expiry} days"

        html_body = f"""  # noqa: E501
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #f5576c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .expiry-box {{ background: #fff3cd; border: 2px solid #ffc107; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                .days {{ font-size: 48px; font-weight: bold; color: #f5576c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Password Expiry Notice</h1>
                </div>
                <div class="content">
                    <p>Hello{' ' + user_name if user_name else ''},</p>

                    <div class="expiry-box">
                        <p class="days">{days_until_expiry}</p>
                        <p><strong>days until your password expires</strong></p>
                    </div>

                    <p>For security reasons, passwords must be changed every {settings.password_expiry_days} days.</p>

                    <p>Please change your password before it expires to avoid account disruption.</p>

                    <p style="text-align: center;">
                        <a href="http://localhost:8000/change-password" class="button">Change Password Now</a>
                    </p>

                    <p><strong>What happens if I don't change it?</strong></p>
                    <ul>
                        <li>Your account will require a password reset</li>
                        <li>You won't be able to login until password is reset</li>
                        <li>Active API keys will continue to work</li>
                    </ul>

                    <p>Best regards,<br>
                    <strong>Vibe Coding Team</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            user_id=user_id,
            email_type="password_expiry_warning",
        )


# Singleton instance
email_service = EmailService()
