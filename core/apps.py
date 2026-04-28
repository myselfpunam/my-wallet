import os
import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals  # noqa: F401  register signal handlers

        # Start background rent scheduler inside the web process.
        # Skip during management commands that don't need it (migrate, test, etc.)
        _skip_commands = {'test', 'migrate', 'makemigrations', 'collectstatic',
                          'shell', 'createsuperuser', 'run_rent_scheduler'}
        if set(sys.argv) & _skip_commands:
            return

        # In dev with auto-reload Django sets RUN_MAIN='true' only in the
        # worker child — start there to avoid two scheduler instances.
        # In production (gunicorn/uvicorn) RUN_MAIN is unset — start normally.
        run_main = os.environ.get('RUN_MAIN', '')
        if run_main in ('true', ''):
            try:
                from core.scheduler import start_background_scheduler
                start_background_scheduler()
            except Exception:
                pass  # never crash app startup due to scheduler failure
