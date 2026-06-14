from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import structlog

from db.models.user import Grades, DailyChallengeWords, Words

logger = structlog.get_logger("default")

WORDS_PER_DAY = 1
from datetime import datetime

class Command(BaseCommand):
    help = "Schedule daily challenge words for all grades"

    def handle(self, *args, **options):
        with open("/tmp/schedule_cron_test.log", "a") as f:

            f.write(f"Executed at {datetime.now()}\n")
        print("daily ch")
        today = timezone.localdate()
        print(today)

        logger.info(
            "Starting daily challenge words scheduling",
            date=str(today)
        )

        grades = Grades.objects.filter(
            is_active=True
        )
        print(grades)
        for grade in grades:

            existing_today = DailyChallengeWords.objects.filter(
                grade=grade,
                challenge_date=today,
                is_active=True
            ).count()

            words_needed = WORDS_PER_DAY - existing_today

            if words_needed <= 0:
                logger.info(
                    "Daily challenge words already scheduled",
                    grade_id=str(grade.id),
                    count=existing_today
                )
                continue

            used_word_ids = DailyChallengeWords.objects.filter(
                grade=grade
            ).values_list(
                "word_id",
                flat=True
            )

            available_words = (
                Words.objects
                .filter(
                    grade=grade,
                    is_active=True
                )
                .exclude(
                    id__in=used_word_ids
                )
                .order_by("?")[:words_needed]
            )

            if not available_words.exists():
                logger.warning(
                    "No unused words available",
                    grade_id=str(grade.id),
                    grade_name=grade.name
                )
                continue

            with transaction.atomic():

                challenge_words = []

                start_order = existing_today + 1

                for index, word in enumerate(
                    available_words,
                    start=start_order
                ):
                    challenge_words.append(
                        DailyChallengeWords(
                            challenge_date=today,
                            grade=grade,
                            word=word,
                            order=index,
                            is_active=True
                        )
                    )

                DailyChallengeWords.objects.bulk_create(
                    challenge_words,
                    # ignore_conflicts=True
                )

            logger.info(
                "Challenge words scheduled",
                grade_id=str(grade.id),
                grade_name=grade.name,
                words_count=len(challenge_words)
            )

        logger.info(
            "Daily challenge words scheduling completed",
            date=str(today)
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Daily challenge words scheduled successfully."
            )
        )