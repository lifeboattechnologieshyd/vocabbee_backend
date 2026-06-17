from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import structlog

from db.models.user import Grades, DailyChallengeWords, Words

logger = structlog.get_logger("default")

WORDS_PER_DAY = 10
import os

with open("/tmp/env_debug.log", "a") as f:
    f.write("=" * 50 + "\n")
    f.write(f"HOST={os.environ.get('POSTGRES_HOST')}\n")
    f.write(f"PORT={os.environ.get('POSTGRES_PORT')}\n")
    f.write(f"DB={os.environ.get('POSTGRES_DB')}\n")
    f.write(f"USER={os.environ.get('POSTGRES_USER')}\n")

class Command(BaseCommand):
    help = "Schedule daily challenge words for all grades"

    def log(self, message):
        with open("/tmp/schedule_daily_words_debug.log", "a") as f:
            f.write(f"{datetime.now()} : {message}\n")

    def handle(self, *args, **options):

        import os

        with open("/tmp/cron_db_env.log", "w") as f:

            f.write(f"POSTGRES_DB={os.environ.get('POSTGRES_DB')}\n")

            f.write(f"POSTGRES_HOST={os.environ.get('POSTGRES_HOST')}\n")

            f.write(f"POSTGRES_USER={os.environ.get('POSTGRES_USER')}\n")

            f.write(f"POSTGRES_PASSWORD={repr(os.environ.get('POSTGRES_PASSWORD'))}\n")

            f.write(f"POSTGRES_PORT={os.environ.get('POSTGRES_PORT')}\n")

        self.log("=" * 80)
        self.log("CRON STARTED")

        try:
            today = timezone.localdate()
            self.log(f"Today = {today}")

            grades = Grades.objects.filter(is_active=True)

            self.log(f"Active Grades Count = {grades.count()}")

            for grade in grades:

                self.log("-" * 50)
                self.log(f"Processing Grade = {grade.id} - {grade.name}")

                existing_today = DailyChallengeWords.objects.filter(
                    grade=grade,
                    challenge_date=today,
                    is_active=True,
                ).count()

                self.log(f"Existing Today = {existing_today}")

                words_needed = WORDS_PER_DAY - existing_today

                self.log(f"Words Needed = {words_needed}")

                if words_needed <= 0:
                    self.log("Already scheduled. Skipping.")
                    continue

                used_word_ids = list(
                    DailyChallengeWords.objects.filter(
                        grade=grade
                    ).values_list("word_id", flat=True)
                )

                self.log(f"Used Word IDs Count = {len(used_word_ids)}")

                available_words = (
                    Words.objects.filter(
                        grade=grade,
                        is_active=True,
                    )
                    .exclude(id__in=used_word_ids)
                    .order_by("?")
                )

                self.log(
                    f"Available Before Slice = {available_words.count()}"
                )

                available_words = list(available_words[:words_needed])

                self.log(
                    f"Available After Slice = {len(available_words)}"
                )

                if len(available_words) == 0:
                    self.log("No available words. Skipping.")
                    continue

                challenge_words = []

                start_order = existing_today + 1

                for index, word in enumerate(
                    available_words,
                    start=start_order,
                ):
                    self.log(
                        f"Preparing Word = {word.id} {word.word}"
                    )

                    challenge_words.append(
                        DailyChallengeWords(
                            challenge_date=today,
                            grade=grade,
                            word=word,
                            order=index,
                            is_active=True,
                        )
                    )

                self.log(
                    f"Prepared Objects = {len(challenge_words)}"
                )

                with transaction.atomic():
                    DailyChallengeWords.objects.bulk_create(
                        challenge_words
                    )

                inserted = DailyChallengeWords.objects.filter(
                    challenge_date=today,
                    grade=grade,
                    is_active=True,
                ).count()

                self.log(f"Inserted Rows = {inserted}")

            self.log("CRON COMPLETED SUCCESSFULLY")

        except Exception as e:
            import traceback

            self.log(f"ERROR = {str(e)}")
            self.log(traceback.format_exc())
            raise

        self.stdout.write(
            self.style.SUCCESS(
                "Daily challenge words scheduled successfully."
            )
        )