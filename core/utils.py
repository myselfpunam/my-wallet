"""
core/utils.py — Email utilities for My Wallet authentication system.

Responsibilities:
  • Send 6-digit OTP emails for account verification and password reset.
  • Render both HTML and plain-text versions so every mail client works.
  • Return a success/failure boolean so callers can handle send failures gracefully
    without crashing the request.

Configuration (all via .env / environment variables):
  EMAIL_HOST_USER     — your Gmail (or other SMTP) address
  EMAIL_HOST_PASSWORD — App Password (not your real Gmail password)
  DEFAULT_FROM_EMAIL  — display address in "From" header (defaults to EMAIL_HOST_USER)

See .env.example at the project root for a complete list of required variables.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def send_verification_email(user, raw_otp: str) -> bool:
    """
    Send a 6-digit email-verification OTP to *user*.

    Called immediately after the inactive User + PasswordResetToken are created
    during signup.  The raw OTP must be passed here and must NOT be stored
    anywhere in the database.

    Returns True on success, False on any SMTP / rendering failure.
    """
    return _dispatch_otp_email(
        recipient_email=user.email,
        display_name=user.first_name or user.username,
        raw_otp=raw_otp,
        purpose='verification',
    )


def send_password_reset_email(user, raw_otp: str) -> bool:
    """
    Send a 6-digit password-reset OTP to *user*.

    Returns True on success, False on any SMTP / rendering failure.
    """
    return _dispatch_otp_email(
        recipient_email=user.email,
        display_name=user.first_name or user.username,
        raw_otp=raw_otp,
        purpose='password_reset',
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dispatch_otp_email(recipient_email: str, display_name: str, raw_otp: str, purpose: str) -> bool:
    """
    Core send function used by both public helpers.

    purpose must be 'verification' or 'password_reset'.
    """
    try:
        if purpose == 'verification':
            subject = 'Verify your My Wallet account — OTP code'
            html_template = 'core/emails/otp_verification.html'
        else:
            subject = 'Reset your My Wallet password — OTP code'
            html_template = 'core/emails/otp_password_reset.html'

        context = {
            'display_name': display_name,
            'otp_code': raw_otp,
            'expiry_minutes': 10,
            'app_name': 'My Wallet',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
        }

        html_body = render_to_string(html_template, context)
        plain_body = _build_plain_text(display_name, raw_otp, purpose)

        send_mail(
            subject=subject,
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=False,
        )

        logger.info("OTP email [%s] dispatched to %s", purpose, recipient_email)
        return True

    except BadHeaderError:
        logger.error("BadHeaderError sending OTP email [%s] to %s", purpose, recipient_email)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to send OTP email [%s] to %s: %s",
            purpose, recipient_email, exc,
        )
        return False


def _build_plain_text(display_name: str, raw_otp: str, purpose: str) -> str:
    """Fallback plain-text body for mail clients that cannot render HTML."""
    action = "verify your email address" if purpose == 'verification' else "reset your password"
    return (
        f"Hello {display_name},\n\n"
        f"Use the following 6-digit code to {action} on My Wallet:\n\n"
        f"    {raw_otp}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not request this, please ignore this email — your account is safe.\n\n"
        f"— The My Wallet Team\n"
    )
