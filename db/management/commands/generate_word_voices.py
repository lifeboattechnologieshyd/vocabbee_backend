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

            print(
                "TTS Client Initialized Successfully",
                flush=True
            )

        except Exception as e:

            logger.error(
                "Failed to initialize TTS client",
                error=str(e)
            )

            print(
                f"TTS Initialization Failed : {e}",
                flush=True
            )

            return

        pending_words = (
            Words.objects.filter(
                is_active=True,
                voice_status="PENDING"
            )[:1000]
        )

        total_count = pending_words.count()

        if total_count == 0:

            print(
                "No Pending Words Found",
                flush=True
            )

            return

        print(
            f"Pending Words : {total_count}",
            flush=True
        )

        successful = []
        unsuccessful = []

        def generate_tts(
            text,
            path
        ):

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
                        audio_encoding=texttospeech.AudioEncoding.LINEAR16
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

                print(
                    f"Uploading -> {path}/{file_name}",
                    flush=True
                )

                return save_to_s3(
                    path=path,
                    file_obj=audio_file
                )

            except Exception as e:

                print(
                    f"TTS Failed : {text}",
                    flush=True
                )

                print(
                    str(e),
                    flush=True
                )

                return None

        for index, word in enumerate(
            pending_words,
            start=1
        ):

            print(
                "=" * 80,
                flush=True
            )

            print(
                f"Processing {index}/{total_count} : {word.word}",
                flush=True
            )

            try:

                audio_obj, created = (
                    WordAudios.objects.get_or_create(
                        word=word
                    )
                )

                print(
                    f"Audio Object Created : {created}",
                    flush=True
                )

                if not audio_obj.pronunciation_audio_url:

                    print(
                        "Generating Pronunciation...",
                        flush=True
                    )

                    audio_obj.pronunciation_audio_url = (
                        generate_tts(
                            word.word,
                            "words/pronunciation"
                        )
                    )

                if not audio_obj.meaning_audio_url:

                    print(
                        "Generating Meaning...",
                        flush=True
                    )

                    audio_obj.meaning_audio_url = (
                        generate_tts(
                            word.meaning,
                            "words/meaning"
                        )
                    )

                if not audio_obj.usage_audio_url:

                    print(
                        "Generating Usage...",
                        flush=True
                    )

                    audio_obj.usage_audio_url = (
                        generate_tts(
                            word.usage,
                            "words/usage"
                        )
                    )

                if not audio_obj.origin_audio_url:

                    print(
                        "Generating Origin...",
                        flush=True
                    )

                    audio_obj.origin_audio_url = (
                        generate_tts(
                            word.origin,
                            "words/origin"
                        )
                    )

                if not audio_obj.part_of_speech_audio_url:

                    print(
                        "Generating Part Of Speech...",
                        flush=True
                    )

                    audio_obj.part_of_speech_audio_url = (
                        generate_tts(
                            word.part_of_speech,
                            "words/part_of_speech"
                        )
                    )

                audio_obj.save()

                if (
                    audio_obj.pronunciation_audio_url
                    and audio_obj.meaning_audio_url
                    and audio_obj.usage_audio_url
                    and audio_obj.origin_audio_url
                    and audio_obj.part_of_speech_audio_url
                ):

                    word.voice_status = "GENERATED"

                    word.save(
                        update_fields=[
                            "voice_status"
                        ]
                    )

                    successful.append(
                        str(word.id)
                    )

                    print(
                        f"{word.word} -> Voice Status Updated to GENERATED",
                        flush=True
                    )

                else:

                    unsuccessful.append(
                        str(word.id)
                    )

                    print(
                        f"{word.word} -> Some audio files are missing",
                        flush=True
                    )

            except Exception as e:

                unsuccessful.append(
                    str(word.id)
                )

                print(
                    f"Error Processing {word.word}",
                    flush=True
                )

                print(
                    str(e),
                    flush=True
                )

        print(
            "=" * 80,
            flush=True
        )

        print(
            f"Success : {len(successful)}",
            flush=True
        )

        print(
            f"Failed : {len(unsuccessful)}",
            flush=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. Success={len(successful)} Failed={len(unsuccessful)}"
            )
        )