
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

        # Initialize Google TTS client
        try:
            tts_client = texttospeech.TextToSpeechClient()

            print("TTS Client Initialized Successfully", flush=True)

        except Exception as e:

            logger.error(
                "Failed to initialize TTS client",
                error=str(e)
            )

            print(f"TTS Initialization Failed: {e}", flush=True)
            return

        # Fetch pending words
        pending_words = Words.objects.filter(
            is_active=True,
            voice_status="PENDING",
            # is_valid=True
        ).order_by("id")[:1000]

        total_count = pending_words.count()

        if total_count == 0:
            print("No Pending Words Found", flush=True)
            return

        print(f"Pending Words: {total_count}", flush=True)

        successful = []
        unsuccessful = []

        # Generate TTS audio and upload to S3
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

                audio_url = save_to_s3(
                    path=path,
                    file_obj=audio_file
                )

                return audio_url

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

        # Process each pending word
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

                # 1. Pronunciation
                if word.word and not audio_obj.pronunciation_audio_url:

                    print("Generating Pronunciation...", flush=True)

                    audio_obj.pronunciation_audio_url = generate_tts(
                        word.word,
                        "words/pronunciation"
                    )

                # 2. Meaning
                if word.meaning and not audio_obj.meaning_audio_url:

                    print("Generating Meaning...", flush=True)

                    audio_obj.meaning_audio_url = generate_tts(
                        word.meaning,
                        "words/meaning"
                    )

                # 3. Usage
                if word.usage and not audio_obj.usage_audio_url:

                    print("Generating Usage...", flush=True)

                    audio_obj.usage_audio_url = generate_tts(
                        word.usage,
                        "words/usage"
                    )

                # 4. Origin
                if word.origin and not audio_obj.origin_audio_url:

                    print("Generating Origin...", flush=True)

                    audio_obj.origin_audio_url = generate_tts(
                        word.origin,
                        "words/origin"
                    )

                # 5. Part of Speech
                if word.part_of_speech and not audio_obj.part_of_speech_audio_url:

                    print("Generating Part Of Speech...", flush=True)

                    audio_obj.part_of_speech_audio_url = generate_tts(
                        word.part_of_speech,
                        "words/part_of_speech"
                    )

                # 6. Phonetic Script
                if word.phonetic_script and not audio_obj.phonetic_script_audio_url:

                    print("Generating Phonetic Script...", flush=True)

                    audio_obj.phonetic_script_audio_url = generate_tts(
                        word.phonetic_script,
                        "words/phonetic_script"
                    )

                # 7. Syllabified Stressed Transcript
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

                # Save audio URLs
                audio_obj.save()

                # Check all applicable audio files
                audio_checks = [
                    (
                        "pronunciation",
                        word.word,
                        audio_obj.pronunciation_audio_url
                    ),
                    (
                        "meaning",
                        word.meaning,
                        audio_obj.meaning_audio_url
                    ),
                    (
                        "usage",
                        word.usage,
                        audio_obj.usage_audio_url
                    ),
                    (
                        "origin",
                        word.origin,
                        audio_obj.origin_audio_url
                    ),
                    (
                        "part_of_speech",
                        word.part_of_speech,
                        audio_obj.part_of_speech_audio_url
                    ),
                    (
                        "phonetic_script",
                        word.phonetic_script,
                        audio_obj.phonetic_script_audio_url
                    ),
                    (
                        "syllabified_stressed_transcript",
                        word.syllabified_stressed_transcript,
                        audio_obj.syllabified_stressed_transcript_audio_url
                    ),
                ]

                # Find missing audio files for populated source fields
                missing_audio = [
                    field_name
                    for field_name, source_text, audio_url in audio_checks
                    if source_text and not audio_url
                ]

                # Update voice status
                if not missing_audio:

                    word.voice_status = "GENERATED"

                    successful.append(str(word.id))

                    print(
                        f"{word.word} -> Voice Status Updated to GENERATED",
                        flush=True
                    )

                else:

                    word.voice_status = "PENDING"

                    unsuccessful.append(str(word.id))

                    print(
                        f"{word.word} -> Missing audio: "
                        f"{', '.join(missing_audio)}",
                        flush=True
                    )

                word.save(update_fields=["voice_status"])

                # Print audio generation status
                audio_status = {
                    "pronunciation": bool(audio_obj.pronunciation_audio_url),
                    "meaning": bool(audio_obj.meaning_audio_url),
                    "usage": bool(audio_obj.usage_audio_url),
                    "origin": bool(audio_obj.origin_audio_url),
                    "part_of_speech": bool(audio_obj.part_of_speech_audio_url),
                    "phonetic_script": bool(audio_obj.phonetic_script_audio_url),
                    "syllabified_stressed_transcript": bool(
                        audio_obj.syllabified_stressed_transcript_audio_url
                    ),
                }

                print(
                    "Audio Generation Status:",
                    audio_status,
                    flush=True
                )

            except Exception as e:

                word.voice_status = "PENDING"
                word.save(update_fields=["voice_status"])

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

        # Final summary
        print("=" * 80, flush=True)

        print(f"Success: {len(successful)}", flush=True)
        print(f"Failed: {len(unsuccessful)}", flush=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. Success={len(successful)} "
                f"Failed={len(unsuccessful)}"
            )
        )

