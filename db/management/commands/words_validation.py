import json
import os
import time

import structlog

from django.core.management.base import BaseCommand
from django.utils import timezone

from google import genai

from db.models import Words

logger = structlog.get_logger("default")


class Command(BaseCommand):
    help = "Validate words using Gemini AI"

    MAX_RETRIES = 5
    RETRY_DELAY = 60

    def handle(self, *args, **options):

        logger.info("validate_words command started")

        try:

            client = genai.Client(
                api_key=os.environ["GEMINI_API_KEY"]
            )

            print(
                "Gemini Client Initialized Successfully",
                flush=True
            )

        except Exception as e:

            logger.error(
                "Failed to initialize Gemini client",
                error=str(e)
            )

            print(
                f"Gemini Initialization Failed : {e}",
                flush=True
            )

            return

        pending_words = (
            Words.objects.filter(
                is_active=True,
                validation_source__isnull=True
            ).order_by("word")[:1000]
        )

        total_count = pending_words.count()

        if total_count == 0:
            print("No Pending Words Found", flush=True)
            return

        print(f"Pending Words : {total_count}", flush=True)

        successful = []
        unsuccessful = []

        for index, word in enumerate(
            pending_words,
            start=1
        ):

            print("=" * 80, flush=True)
            print(
                f"Processing {index}/{total_count} : {word.word}",
                flush=True
            )

            prompt = f"""
You are an English dictionary expert.

Determine whether the following is a valid English word.

Treat these as VALID:
- Standard English words
- Scientific terms
- Biology terms
- Chemistry terms
- Physics terms
- Mathematics terms
- Geography terms
- History terms
- Educational vocabulary

Return ONLY JSON.

{{
    "is_valid": true,
    "reason": "Short reason"
}}

Word: "{word.word}"
"""

            result = None

            try:

                for attempt in range(self.MAX_RETRIES):

                    try:

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                        )

                        text = response.text.strip()

                        if text.startswith("```"):
                            text = (
                                text.replace("```json", "")
                                .replace("```", "")
                                .strip()
                            )

                        result = json.loads(text)
                        break

                    except Exception as e:

                        if "RESOURCE_EXHAUSTED" in str(e):

                            print(
                                f"Rate limit reached. Waiting {self.RETRY_DELAY} seconds...",
                                flush=True
                            )

                            time.sleep(self.RETRY_DELAY)
                            continue

                        raise

                if result is None:
                    raise Exception(
                        "Maximum retry attempts exceeded."
                    )

                word.is_valid = result.get(
                    "is_valid",
                    False
                )

                word.validation_reason = result.get(
                    "reason",
                    ""
                )

                word.validation_source = "AI"

                word.validated_at = timezone.now()

                word.save(
                    update_fields=[
                        "is_valid",
                        "validation_reason",
                        "validation_source",
                        "validated_at",
                    ]
                )

                successful.append(str(word.id))

                print(
                    f"{word.word} -> Valid : {word.is_valid}",
                    flush=True
                )

            except Exception as e:

                unsuccessful.append(str(word.id))

                logger.error(
                    "word_validation_failed",
                    word=word.word,
                    error=str(e),
                )

                print(
                    f"Validation Failed : {word.word}",
                    flush=True
                )

                print(str(e), flush=True)

        print("=" * 80)
        print(f"Success : {len(successful)}")
        print(f"Failed : {len(unsuccessful)}")