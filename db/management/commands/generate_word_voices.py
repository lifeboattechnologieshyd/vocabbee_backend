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

            print("TTS Client Initialized Successfully")

        except Exception as e:

            print(f"TTS Client Initialization Failed : {e}")

            logger.error(
                "Failed to initialize TTS client",
                error=str(e)
            )

            return

        pending_words = (
            Words.objects.filter(
                is_active=True,
                voice_status="PENDING"
            )[:1000]
        )

        if not pending_words.exists():

            print("No Pending Words Found")

            return

        print(
            f"Pending Words Count : {pending_words.count()}"
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
                    f"Uploading : {path}/{file_name}"
                )

                return save_to_s3(
                    path=path,
                    file_obj=audio_file
                )

            except Exception as e:

                print(
                    f"TTS Failed : {text}"
                )

                print(str(e))

                return None

        for index, word in enumerate(
            pending_words,
            start=1
        ):

            print(
                "=" * 80
            )

            print(
                f"Processing {index} / {pending_words.count()} : {word.word}"
            )

            try:

                audio_obj, created = (
                    WordAudios.objects.get_or_create(
                        word=word
                    )
                )

                print(
                    f"Audio Object Created : {created}"
                )

                if not audio_obj.pronunciation_audio_url:

                    print(
                        "Generating Pronunciation..."
                    )

                    audio_obj.pronunciation_audio_url = (
                        generate_tts(
                            word.word,
                            "words/pronunciation"
                        )
                    )

                else:

                    print(
                        "Pronunciation Already Exists"
                    )

                if not audio_obj.meaning_audio_url:

                    print(
                        "Generating Meaning..."
                    )

                    audio_obj.meaning_audio_url = (
                        generate_tts(
                            word.meaning,
                            "words/meaning"
                        )
                    )

                else:

                    print(
                        "Meaning Already Exists"
                    )

                if not audio_obj.usage_audio_url:

                    print(
                        "Generating Usage..."
                    )

                    audio_obj.usage_audio_url = (
                        generate_tts(
                            word.usage,
                            "words/usage"
                        )
                    )

                else:

                    print(
                        "Usage Already Exists"
                    )

                if not audio_obj.origin_audio_url:

                    print(
                        "Generating Origin..."
                    )

                    audio_obj.origin_audio_url = (
                        generate_tts(
                            word.origin,
                            "words/origin"
                        )
                    )

                else:

                    print(
                        "Origin Already Exists"
                    )

                if not audio_obj.part_of_speech_audio_url:

                    print(
                        "Generating Part Of Speech..."
                    )

                    audio_obj.part_of_speech_audio_url = (
                        generate_tts(
                            word.part_of_speech,
                            "words/part_of_speech"
                        )
                    )

                else:

                    print(
                        "Part Of Speech Already Exists"
                    )

                audio_obj.save()

                print(
                    "Audio Object Saved"
                )

                if (
                    audio_obj.pronunciation_audio_url
                    and audio_obj.meaning_audio_url
                    and audio_obj.usage_audio_url
                    and audio_obj.origin_audio_url
                    and audio_obj.part_of_speech_audio_url
                ):

                    word.voice_status = (
                        "GENERATED"
                    )

                    word.save(
                        update_fields=[
                            "voice_status"
                        ]
                    )

                    print(
                        f"{word.word} -> Voice Status Updated to GENERATED"
                    )

                    successful.append(
                        str(word.id)
                    )

                else:

                    print(
                        f"{word.word} -> Some audio files are missing"
                    )

                    unsuccessful.append(
                        {
                            "word": word.word,
                            "reason": "Some audio files are missing"
                        }
                    )

            except Exception as e:

                print(
                    f"Error Processing {word.word}"
                )

                print(
                    str(e)
                )

                unsuccessful.append(
                    {
                        "word": word.word,
                        "reason": str(e)
                    }
                )

        print(
            "=" * 80
        )

        print(
            f"Success Count : {len(successful)}"
        )

        print(
            f"Failed Count : {len(unsuccessful)}"
        )

        logger.info(
            "Word audio generation completed",
            success_count=len(successful),
            failed_count=len(unsuccessful)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. Success={len(successful)} Failed={len(unsuccessful)}"
            )
        )