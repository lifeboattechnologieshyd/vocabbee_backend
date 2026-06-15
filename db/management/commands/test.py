from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test cron execution"

    def handle(self, *args, **options):
        with open("/tmp/test_cron.log", "a") as f:
            f.write("=" * 50 + "\n")
            f.write(f"Executed at: {datetime.now()}\n")
            f.write(f"DATABASE: {settings.DATABASES['default']}\n")
            f.write("Cron is working successfully!\n")