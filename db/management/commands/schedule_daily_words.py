from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import structlog

from db.models.user import Grades, DailyChallengeWords, Words

logger = structlog.get_logger("default")

WORDS_PER_DAY = 1
from datetime import datetime

from datetime import datetime
from django.conf import settings

print(settings.DATABASES["default"])
class Command(BaseCommand):
    help = "Schedule daily challenge words for all grades"

    def handle(self, *args, **options):

        with open("/tmp/schedule_cron_test.log", "a") as f:
            f.write(f"Executed at {datetime.now()}\n")

        today = timezone.localdate()

        print("=" * 60)
        print(f"Today: {today}")

        logger.info(
            "Starting daily challenge words scheduling",
            date=str(today)
        )

        grades = Grades.objects.filter(is_active=True)

        for grade in grades:

            print("=" * 60)
            print(f"Grade: {grade.name}")

            existing_today = DailyChallengeWords.objects.filter(
                grade=grade,
                challenge_date=today,
                is_active=True
            ).count()

            print(f"Existing Today: {existing_today}")

            words_needed = WORDS_PER_DAY - existing_today

            print(f"Words Needed: {words_needed}")

            if words_needed <= 0:
                logger.info(
                    "Daily challenge words already scheduled",
                    grade_id=str(grade.id),
                    count=existing_today
                )
                continue

            used_word_ids = list(
                DailyChallengeWords.objects.filter(
                    grade=grade
                ).values_list(
                    "word_id",
                    flat=True
                )
            )

            print(f"Used Words: {len(used_word_ids)}")

            available_words = (
                Words.objects
                .filter(
                    grade=grade,
                    is_active=True
                )
                .exclude(
                    id__in=used_word_ids
                )
                .order_by("?")
            )

            print(
                f"Available Words Before Slice: {available_words.count()}"
            )

            available_words = available_words[:words_needed]

            print(
                f"Available Words After Slice: {available_words.count()}"
            )

            if not available_words.exists():
                logger.warning(
                    "No unused words available",
                    grade_id=str(grade.id),
                    grade_name=grade.name
                )
                continue

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

            print(f"Prepared Objects: {len(challenge_words)}")

            with transaction.atomic():

                DailyChallengeWords.objects.bulk_create(
                    challenge_words
                )

            inserted = DailyChallengeWords.objects.filter(
                challenge_date=today,
                grade=grade
            ).count()

            print(f"Inserted Rows: {inserted}")

            logger.info(
                "Challenge words scheduled",
                grade_id=str(grade.id),
                grade_name=grade.name,
                inserted=inserted
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