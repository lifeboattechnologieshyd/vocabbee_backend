
import re
import time

import structlog

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from google.cloud import texttospeech

from db.models import Words
from db.models.user import WordAudios
from shared.clients.s3 import save_to_s3


logger = structlog.get_logger("default")


class Command(BaseCommand):

    help = "Generate TTS audio files for words"

    def handle(self, *args, **options):

        logger.info("generate_word_voices command started")

        try:
            tts_client = texttospeech.TextToSpeechClient()

            print(
                "TTS Client Initialized Successfully",
                flush=True
            )

        except Exception as e:

            logger.error(
                "Failed to initialize TTS client",
                error=str(e)
            )

            print(f"TTS Initialization Failed: {e}", flush=True)
            return

        pending_words = Words.objects.filter(
            is_active=True,
            voice_status="PENDING",
            # is_valid=True
        )[:10000]

        total_count = pending_words.count()

        if total_count == 0:
            print("No Pending Words Found", flush=True)
            return

        print(f"Pending Words: {total_count}", flush=True)

        successful = []
        unsuccessful = []

        def generate_tts(text, path):

            if not text or not str(text).strip():
                return None

            try:

                synthesis_input = texttospeech.SynthesisInput(
                    text=str(text).strip()
                )

                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-IN",
                    name="en-IN-Chirp3-HD-Callirrhoe"
                )

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16
                )

                response = tts_client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )

                safe_text = re.sub(
                    r"\W+",
                    "_",
                    str(text)
                )[:50]

                file_name = f"{safe_text}_{int(time.time())}.wav"

                audio_file = ContentFile(response.audio_content)
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

                logger.error(
                    "TTS generation failed",
                    text=str(text),
                    path=path,
                    error=str(e)
                )

                print(f"TTS Failed: {text}", flush=True)
                print(str(e), flush=True)

                return None

        for index, word in enumerate(pending_words, start=1):

            print("=" * 80, flush=True)

            print(
                f"Processing {index}/{total_count}: {word.word}",
                flush=True
            )

            try:

                audio_obj, created = WordAudios.objects.get_or_create(
                    word=word
                )

                print(
                    f"Audio Object Created: {created}",
                    flush=True
                )

                # Pronunciation
                if word.word and not audio_obj.pronunciation_audio_url:

                    print("Generating Pronunciation...", flush=True)

                    audio_obj.pronunciation_audio_url = generate_tts(
                        word.word,
                        "words/pronunciation"
                    )

                # Meaning
                if word.meaning and not audio_obj.meaning_audio_url:

                    print("Generating Meaning...", flush=True)

                    audio_obj.meaning_audio_url = generate_tts(
                        word.meaning,
                        "words/meaning"
                    )

                # Usage
                if word.usage and not audio_obj.usage_audio_url:

                    print("Generating Usage...", flush=True)

                    audio_obj.usage_audio_url = generate_tts(
                        word.usage,
                        "words/usage"
                    )

                # Origin
                if word.origin and not audio_obj.origin_audio_url:

                    print("Generating Origin...", flush=True)

                    audio_obj.origin_audio_url = generate_tts(
                        word.origin,
                        "words/origin"
                    )

                # Part of Speech
                if word.part_of_speech and not audio_obj.part_of_speech_audio_url:

                    print("Generating Part Of Speech...", flush=True)

                    audio_obj.part_of_speech_audio_url = generate_tts(
                        word.part_of_speech,
                        "words/part_of_speech"
                    )

                # NEW: Phonetic Script
                if word.phonetic_script and not audio_obj.phonetic_script_audio_url:

                    print("Generating Phonetic Script...", flush=True)

                    audio_obj.phonetic_script_audio_url = generate_tts(
                        word.phonetic_script,
                        "words/phonetic_script"
                    )

                # NEW: Syllabified Stressed Transcript
                if (
                    word.syllabified_stressed_transcript
                    and not audio_obj.syllabified_stressed_transcript_audio_url
                ):

                    print(
                        "Generating Syllabified Stressed Transcript...",
                        flush=True
                    )

                    audio_obj.syllabified_stressed_transcript_audio_url = (
                        generate_tts(
                            word.syllabified_stressed_transcript,
                            "words/syllabified_stressed_transcript"
                        )
                    )

                audio_obj.save()

                # Check whether all applicable audio files are generated.
                audio_checks = [
                    (word.word, audio_obj.pronunciation_audio_url),
                    (word.meaning, audio_obj.meaning_audio_url),
                    (word.usage, audio_obj.usage_audio_url),
                    (word.origin, audio_obj.origin_audio_url),
                    (word.part_of_speech, audio_obj.part_of_speech_audio_url),
                    (word.phonetic_script, audio_obj.phonetic_script_audio_url),
                    (
                        word.syllabified_stressed_transcript,
                        audio_obj.syllabified_stressed_transcript_audio_url
                    ),
                ]

                all_audio_generated = all(
                    not source_text or audio_url
                    for source_text, audio_url in audio_checks
                )

                if all_audio_generated:

                    word.voice_status = "GENERATED"

                    word.save(
                        update_fields=["voice_status"]
                    )

                    successful.append(str(word.id))

                    print(
                        f"{word.word} -> Voice Status Updated to GENERATED",
                        flush=True
                    )

                else:

                    unsuccessful.append(str(word.id))

                    print(
                        f"{word.word} -> Some audio files are missing",
                        flush=True
                    )

            except Exception as e:

                unsuccessful.append(str(word.id))

                logger.error(
                    "Error processing word",
                    word=word.word,
                    error=str(e)
                )

                print(
                    f"Error Processing {word.word}: {e}",
                    flush=True
                )

        print("=" * 80, flush=True)

        print(f"Success: {len(successful)}", flush=True)
        print(f"Failed: {len(unsuccessful)}", flush=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. Success={len(successful)} "
                f"Failed={len(unsuccessful)}"
            )
        )
