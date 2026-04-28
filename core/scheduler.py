"""
core/scheduler.py — Payment Reminder automation jobs for My Wallet.

Two jobs run on a daily cron schedule:

  generate_reminder_entries()
    Runs at 00:05 each day.
    Creates ReminderEntry rows for active PaymentReminders:
    - one_time  → one entry at the reminder's due_date
    - monthly   → one entry per month using the reminder's day-of-month,
                  generated for current + next month.
    Uses get_or_create so it is fully idempotent.

  send_payment_reminders()
    Runs at 08:00 each day.
    Sends one reminder email per pending entry whose due-date is within the
    user-configured reminder window.  Tracks last_reminder_date so at most
    one email is sent per entry per day.

start_background_scheduler()
    Called from CoreConfig.ready().  Starts an APScheduler BackgroundScheduler
    with MemoryJobStore (no DB access at startup).
"""

import logging
import calendar
from datetime import date

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_due_date(year: int, month: int, day: int) -> date:
    """Return date(year, month, day), capping day at the last day of the month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _month_iter(year: int, month: int, count: int = 2):
    """Yield (year, month) tuples for *count* consecutive months starting at year/month."""
    for _ in range(count):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


# ── job functions ─────────────────────────────────────────────────────────────

def generate_reminder_entries():
    """
    Create ReminderEntry rows for all active PaymentReminders.
    - one_time  → single entry at reminder.due_date
    - monthly   → entries for current + next month using day-of-month from due_date
    Safe to call repeatedly — get_or_create prevents duplicates.
    """
    from .models import PaymentReminder, ReminderEntry

    today = date.today()
    created_count = 0

    for reminder in PaymentReminder.objects.filter(is_active=True).select_related('user'):
        if reminder.frequency == PaymentReminder.FREQ_ONE_TIME:
            _, created = ReminderEntry.objects.get_or_create(
                reminder=reminder,
                due_date=reminder.due_date,
                defaults={
                    'user':   reminder.user,
                    'amount': reminder.amount,
                    'status': ReminderEntry.STATUS_PENDING,
                },
            )
            if created:
                created_count += 1
                logger.info("Created one-time entry: %s on %s for user %s",
                            reminder.title, reminder.due_date, reminder.user)

        else:  # monthly
            day = reminder.due_date.day
            first_month = date(reminder.due_date.year, reminder.due_date.month, 1)

            for y, m in _month_iter(today.year, today.month, count=2):
                if date(y, m, 1) < first_month:
                    continue
                due = _safe_due_date(y, m, day)
                _, created = ReminderEntry.objects.get_or_create(
                    reminder=reminder,
                    due_date=due,
                    defaults={
                        'user':   reminder.user,
                        'amount': reminder.amount,
                        'status': ReminderEntry.STATUS_PENDING,
                    },
                )
                if created:
                    created_count += 1
                    logger.info("Created monthly entry: %s %s/%s for user %s",
                                reminder.title, m, y, reminder.user)

    logger.info("generate_reminder_entries: %d new entries created", created_count)
    return created_count


def send_payment_reminders():
    """
    Send reminder emails for pending ReminderEntry rows whose due-date falls
    within the user-configured remind_days_before window.
    At most one email per entry per day (tracked via last_reminder_date).
    """
    from .models import ReminderEntry
    from .utils import send_payment_reminder_email

    today = date.today()
    sent_count = 0

    pending_entries = (
        ReminderEntry.objects
        .filter(status=ReminderEntry.STATUS_PENDING)
        .select_related('reminder', 'user')
    )

    for entry in pending_entries:
        if entry.last_reminder_date == today:
            continue

        days_until = (entry.due_date - today).days
        remind_before = entry.reminder.remind_days_before

        if days_until > remind_before:
            continue

        if not entry.user.email:
            continue

        sent = send_payment_reminder_email(entry)
        if sent:
            entry.last_reminder_date = today
            entry.save(update_fields=['last_reminder_date', 'updated_at'])
            sent_count += 1

    logger.info("send_payment_reminders: %d reminder emails sent", sent_count)
    return sent_count


# ── scheduler lifecycle ───────────────────────────────────────────────────────

_scheduler_started = False


def start_background_scheduler():
    """
    Start the APScheduler BackgroundScheduler embedded in the web process.
    Called from CoreConfig.ready().  Uses MemoryJobStore to avoid DB access
    at startup.  A module-level flag prevents double-start.
    """
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone='UTC')

        scheduler.add_job(
            generate_reminder_entries,
            trigger=CronTrigger(hour=0, minute=5),
            id='generate_reminder_entries',
            name='Generate Payment Reminder Entries',
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            send_payment_reminders,
            trigger=CronTrigger(hour=8, minute=0),
            id='send_payment_reminders',
            name='Send Payment Reminder Emails',
            replace_existing=True,
            misfire_grace_time=3600,
        )

        scheduler.start()
        logger.info("Payment reminder background scheduler started (MemoryJobStore)")

    except Exception as exc:
        logger.error("Payment reminder scheduler failed to start: %s", exc)
        _scheduler_started = False
