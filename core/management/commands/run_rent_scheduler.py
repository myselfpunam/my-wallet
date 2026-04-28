"""
Management command: run_rent_scheduler

Runs the payment reminder automation jobs in a persistent foreground process
using APScheduler's BlockingScheduler.  Use this when you want to run the
scheduler as an independent OS-managed process (systemd, Windows Task Scheduler)
instead of embedding it inside the Django web process.

Also executes both jobs once immediately on startup so you don't have to wait
for the first cron tick.

Usage:
    python manage.py run_rent_scheduler

Deployment (Linux systemd example):
    [Service]
    ExecStart=/path/to/venv/bin/python manage.py run_rent_scheduler
    Restart=always

Windows Task Scheduler:
    Action: python manage.py run_rent_scheduler
    Schedule: At system startup / daily
"""

import logging

from django.core.management.base import BaseCommand

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from core.scheduler import generate_reminder_entries, send_payment_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the payment reminder scheduler as a persistent foreground process'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting payment reminder scheduler…'))

        self.stdout.write('  → Running generate_reminder_entries()…')
        created = generate_reminder_entries()
        self.stdout.write(self.style.SUCCESS(f'     {created} new entry/entries created.'))

        self.stdout.write('  → Running send_payment_reminders()…')
        sent = send_payment_reminders()
        self.stdout.write(self.style.SUCCESS(f'     {sent} reminder email(s) sent.'))

        scheduler = BlockingScheduler(timezone='UTC')

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

        self.stdout.write(
            self.style.SUCCESS(
                'Scheduler running. Jobs fire daily at 00:05 (entries) and 08:00 (reminders).\n'
                'Press Ctrl+C to stop.'
            )
        )

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=False)
            self.stdout.write(self.style.WARNING('Scheduler stopped.'))
