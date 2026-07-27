import json
import time

import structlog

from django.core.management.base import BaseCommand
from django.utils import timezone

from google import genai
from google.auth import default

from db.models import Words

logger = structlog.get_logger("default")


class Command(BaseCommand):
    help = "Validate words using Gemini AI (Vertex AI)"

    MAX_RETRIES = 5
    RETRY_DELAY = 60

    def handle(self, *args, **options):

        logger.info("validate_words command started")

        # ------------------------------------------------------------------
        # Initialize Vertex AI Client
        # ------------------------------------------------------------------
        try:
            credentials, project = default()

            client = genai.Client(
                vertexai=True,
                project=project,
                location="global",
            )

            logger.info(
                "gemini_client_initialized",
                project=project,
                service_account=getattr(
                    credentials,
                    "service_account_email",
                    "Unknown",
                ),
            )

            print(
                f"Gemini Vertex AI Client Initialized (Project: {project})",
                flush=True,
            )

        except Exception as e:

            logger.exception(
                "gemini_client_initialization_failed",
                error=str(e),
            )

            print(
                f"Gemini Initialization Failed: {e}",
                flush=True,
            )

            return

        # ------------------------------------------------------------------
        # Fetch pending words
        # ------------------------------------------------------------------
        pending_words = (
            Words.objects.filter(
                is_active=True,
                validation_source__isnull=True,
            )
            .order_by("word")[:1000]
        )

        total_count = pending_words.count()

        if total_count == 0:
            print("No Pending Words Found", flush=True)
            return

        print(f"Pending Words: {total_count}", flush=True)

        successful = []
        unsuccessful = []

        # ------------------------------------------------------------------
        # Process each word
        # ------------------------------------------------------------------
        for index, word in enumerate(
            pending_words,
            start=1,
        ):

            print("=" * 80, flush=True)
            print(
                f"Processing {index}/{total_count}: {word.word}",
                flush=True,
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

Return ONLY valid JSON.

{{
    "is_valid": true,
    "reason": "Short reason"
}}

Word: "{word.word}"
"""

            result = None

            for attempt in range(1, self.MAX_RETRIES + 1):

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

                    error = str(e)

                    retryable = (
                        "RESOURCE_EXHAUSTED" in error
                        or "429" in error
                        or "503" in error
                    )

                    logger.warning(
                        "gemini_validation_attempt_failed",
                        word=word.word,
                        attempt=attempt,
                        retryable=retryable,
                        error=error,
                    )

                    if retryable and attempt < self.MAX_RETRIES:

                        print(
                            f"Retrying in {self.RETRY_DELAY} seconds "
                            f"({attempt}/{self.MAX_RETRIES})...",
                            flush=True,
                        )

                        time.sleep(self.RETRY_DELAY)
                        continue

                    result = None
                    break

            if result is None:

                unsuccessful.append(str(word.id))

                logger.error(
                    "word_validation_failed",
                    word=word.word,
                )

                print(
                    f"Validation Failed: {word.word}",
                    flush=True,
                )

                continue

            try:

                word.is_valid = result.get(
                    "is_valid",
                    False,
                )

                word.validation_reason = result.get(
                    "reason",
                    "",
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
                    f"{word.word} -> Valid: {word.is_valid}",
                    flush=True,
                )

            except Exception as e:

                unsuccessful.append(str(word.id))

                logger.exception(
                    "word_save_failed",
                    word=word.word,
                    error=str(e),
                )

                print(
                    f"Failed to save: {word.word}",
                    flush=True,
                )

        print("=" * 80, flush=True)
        print(f"Success: {len(successful)}", flush=True)
        print(f"Failed : {len(unsuccessful)}", flush=True)

        logger.info(
            "validate_words_completed",
            total=total_count,
            successful=len(successful),
            failed=len(unsuccessful),
        )