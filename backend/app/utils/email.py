import logging

logger = logging.getLogger(__name__)


async def send_password_reset_email(to_email: str, reset_token: str, reset_url: str) -> None:
    """Send password reset email. Logs token in development when SMTP is not configured."""
    reset_link = f"{reset_url}?token={reset_token}"
    logger.info("Password reset link for %s: %s", to_email, reset_link)

    # SMTP integration placeholder — configure SMTP_* env vars for production
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.smtp_host:
            return

        import smtplib
        from email.message import EmailMessage

        message = EmailMessage()
        message["Subject"] = "SmartStudy Password Reset"
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message.set_content(
            f"Reset your SmartStudy password using this link (valid for 1 hour):\n\n{reset_link}"
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:
        logger.error("Failed to send reset email: %s", exc)
