# db/management/commands/test_env.py

from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open("/tmp/cron_env.log", "w") as f:
            for k, v in sorted(os.environ.items()):
                f.write(f"{k}={v}\n")