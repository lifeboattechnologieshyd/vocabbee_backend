import re
import time

import structlog

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from google.cloud import texttospeech

from db.models import Words
from db.models.user import WordAudios
from shared.clients.s3 import save_to_s3

logger = structlog.get_logger("default")


class Command(BaseCommand):
    help = "Generate TTS audio files for words"

    def handle(self, *args, **options):

        logger.info(
            "generate_word_voices command started"
        )

        try:
            tts_client = (
                texttospeech.TextToSpeechClient()
            )

            logger.info(
                "TTS client initialized successfully"
            )

        except Exception as e:

            logger.error(
                "Failed to initialize TTS client",
                error=str(e)
            )

            return

        pending_words = (
            Words.objects
            .filter(
                is_active=True,
                voice_status="PENDING"
            )[:1000]
        )

        if not pending_words.exists():

            logger.info(
                "No pending words found"
            )

            return

        total_count = pending_words.count()

        logger.info(
            "Pending words found",
            count=total_count
        )

        successful = []
        unsuccessful = []

        def generate_tts(text, path):

            if not text:
                return None

            if not str(text).strip():
                return None

            try:

                synthesis_input = (
                    texttospeech.SynthesisInput(
                        text=str(text)
                    )
                )

                voice = (
                    texttospeech.VoiceSelectionParams(
                        language_code="en-IN",
                        name="en-IN-Chirp3-HD-Callirrhoe"
                    )
                )

                audio_config = (
                    texttospeech.AudioConfig(
                        audio_encoding=
                        texttospeech.AudioEncoding.LINEAR16
                    )
                )

                response = (
                    tts_client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                )

                safe_text = re.sub(
                    r"\W+",
                    "_",
                    str(text)
                )[:50]

                file_name = (
                    f"{safe_text}_{int(time.time())}.wav"
                )

                audio_file = ContentFile(
                    response.audio_content
                )

                audio_file.name = file_name

                return save_to_s3(
                    path=path,
                    file_obj=audio_file
                )



            except Exception as e:

                logger.error(
                    "TTS generation failed",
                    text=str(text),
                    error=str(e)
                )

                return None

        for index, word in enumerate(
            pending_words,
            start=1
        ):

            try:

                logger.info(
                    "Processing word",
                    current=index,
                    total=total_count,
                    word=word.word
                )

                pronunciation_audio = generate_tts(
                    word.word,
                    "words/pronunciation"
                )

                meaning_audio = generate_tts(
                    word.meaning,
                    "words/meaning"
                )

                usage_audio = generate_tts(
                    word.usage,
                    "words/usage"
                )

                origin_audio = generate_tts(
                    word.origin,
                    "words/origin"
                )

                part_of_speech_audio = generate_tts(
                    word.part_of_speech,
                    "words/part_of_speech"
                )

                if not pronunciation_audio:

                    unsuccessful.append({
                        "word": word.word,
                        "reason": (
                            "Pronunciation audio generation failed"
                        )
                    })

                    continue

                audio_obj, _ = (
                    WordAudios.objects.get_or_create(
                        word=word
                    )
                )

                audio_obj.pronunciation_audio_url = (
                    pronunciation_audio
                )

                audio_obj.meaning_audio_url = (
                    meaning_audio
                )

                audio_obj.usage_audio_url = (
                    usage_audio
                )

                audio_obj.origin_audio_url = (
                    origin_audio
                )

                audio_obj.part_of_speech_audio_url = (
                    part_of_speech_audio
                )

                audio_obj.save()

                successful.append(
                    str(word.id)
                )

                logger.info(
                    "Audio generated successfully",
                    word=word.word
                )

            except Exception as e:

                unsuccessful.append({
                    "word": word.word,
                    "reason": str(e)
                })

                logger.error(
                    "Failed processing word",
                    word=word.word,
                    error=str(e)
                )

        logger.info(
            "Word audio generation completed",
            success_count=len(successful),
            failed_count=len(unsuccessful)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. "
                f"Success={len(successful)} "
                f"Failed={len(unsuccessful)}"
            )
        )