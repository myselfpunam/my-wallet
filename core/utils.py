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


def send_payment_reminder_email(entry) -> bool:
    """
    Send a payment reminder email for *entry* (a ReminderEntry instance).
    Returns True on success, False on any failure.
    """
    from datetime import date

    user = entry.user
    today = date.today()
    days_until = (entry.due_date - today).days

    if days_until < 0:
        reminder_type = 'overdue'
    elif days_until == 0:
        reminder_type = 'due_today'
    else:
        reminder_type = 'upcoming'

    title = entry.reminder.title
    abs_days = abs(days_until)

    subject_map = {
        'upcoming':  f"Payment Reminder: {title} — due in {days_until} day{'s' if days_until != 1 else ''}",
        'due_today': f"Payment Due Today: {title} — My Wallet",
        'overdue':   f"Overdue Payment: {title} — {abs_days} day{'s' if abs_days != 1 else ''} overdue",
    }

    context = {
        'display_name':  user.first_name or user.username,
        'title':         title,
        'icon':          entry.reminder.get_icon(),
        'amount':        entry.amount or entry.reminder.amount,
        'due_date':      entry.due_date,
        'days_until':    days_until,
        'reminder_type': reminder_type,
        'app_name':      'My Wallet',
    }

    try:
        html_body  = render_to_string('core/emails/payment_reminder.html', context)
        plain_body = _build_payment_plain_text(context)
        send_mail(
            subject=subject_map[reminder_type],
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info("Payment reminder [%s] sent to %s for %s", reminder_type, user.email, entry)
        return True
    except BadHeaderError:
        logger.error("BadHeaderError sending payment reminder to %s", user.email)
        return False
    except Exception as exc:
        logger.error("Failed to send payment reminder to %s: %s", user.email, exc)
        return False


def _build_payment_plain_text(ctx: dict) -> str:
    days = ctx['days_until']
    title = ctx['title']
    if ctx['reminder_type'] == 'overdue':
        timing = f'"{title}" is {abs(days)} day{"s" if abs(days) != 1 else ""} OVERDUE.'
    elif ctx['reminder_type'] == 'due_today':
        timing = f'"{title}" is due TODAY.'
    else:
        timing = f'"{title}" is due in {days} day{"s" if days != 1 else ""}.'

    amount_line = f"  Amount   : £{ctx['amount']}\n" if ctx['amount'] else ''
    return (
        f"Hello {ctx['display_name']},\n\n"
        f"{timing}\n\n"
        f"  Payment  : {title}\n"
        f"{amount_line}"
        f"  Due Date : {ctx['due_date'].strftime('%d %B %Y')}\n\n"
        f"Log in to My Wallet to mark this payment as done.\n\n"
        f"— The My Wallet Team\n"
    )


def send_account_deletion_email(user, raw_otp: str) -> bool:
    """
    Send a 6-digit OTP to confirm account deletion.
    Returns True on success, False on any failure.
    """
    try:
        context = {
            'display_name': user.first_name or user.username,
            'otp_code': raw_otp,
            'expiry_minutes': 10,
            'app_name': 'My Wallet',
        }
        plain_body = (
            f"Hello {context['display_name']},\n\n"
            f"You requested to permanently delete your My Wallet account.\n\n"
            f"Your confirmation code is:\n\n"
            f"    {raw_otp}\n\n"
            f"This code expires in 10 minutes.\n\n"
            f"If you did NOT request this, please ignore this email and change your password immediately.\n\n"
            f"WARNING: This action is irreversible. All your data will be permanently deleted.\n\n"
            f"— The My Wallet Team\n"
        )
        send_mail(
            subject='Confirm account deletion — My Wallet',
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Account deletion OTP sent to %s", user.email)
        return True
    except BadHeaderError:
        logger.error("BadHeaderError sending deletion OTP to %s", user.email)
        return False
    except Exception as exc:
        logger.error("Failed to send deletion OTP to %s: %s", user.email, exc)
        return False


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
