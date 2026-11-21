from db.models.user import KidWordProgress, Words, WordAudios
import random
import requests

#######################################
##
## this will be used to fetch and serve the questions
## in practice mode. used in start api, submit api and skip api.
##
######################################

def get_practice_words(kid, no_of_questions=10):

    print("\n========== GET PRACTICE WORDS STARTED ==========")

    print("Kid ID:", kid.id)
    print("Grade ID:", kid.grade_id)
    print("Requested Questions:", no_of_questions)

    attempted_word_ids = KidWordProgress.objects.filter(
        kid=kid
    ).values_list(
        "word_id",
        flat=True
    )

    attempted_count = attempted_word_ids.count()

    print("Previously Attempted Words Count:", attempted_count)

    selected_words = list(
        Words.objects.filter(
            grade=kid.grade,
            is_active=True,
            voice_status="GENERATED",
            is_valid=True
        ).select_related(
            "audio"
        ).exclude(
            id__in=attempted_word_ids
        ).order_by("?")[:no_of_questions]
    )

    print("Initially Selected Words:", len(selected_words))

    if len(selected_words) < no_of_questions:

        remaining_count = no_of_questions - len(selected_words)

        print("Not Enough Words Available")
        print("Remaining Questions:", remaining_count)

        selected_word_ids = [
            word.id for word in selected_words
        ]

        additional_words = list(
            Words.objects.filter(
                grade=kid.grade,
                is_active=True,
                voice_status="GENERATED",
                is_valid=True
            ).select_related(
                "audio"
            ).exclude(
                id__in=attempted_word_ids
            ).exclude(
                id__in=selected_word_ids
            ).order_by("?")[:remaining_count]
        )

        print("Additional Words Selected:", len(additional_words))

        selected_words.extend(additional_words)

    print("Final Selected Words Count:", len(selected_words))

    response = []

    for index, word in enumerate(selected_words, start=1):

        audio = getattr(word, "audio", None)

        print(f"\n----- WORD {index} -----")
        print("Word ID:", word.id)
        print("Word:", word.word)
        print("Voice Status:", word.voice_status)
        print("Audio Record Exists:", bool(audio))

        if audio:
            print("Pronunciation Audio:", bool(audio.pronunciation_audio_url))
            print("Meaning Audio:", bool(audio.meaning_audio_url))
            print("Part of Speech Audio:", bool(audio.part_of_speech_audio_url))
            print("Origin Audio:", bool(audio.origin_audio_url))
            print("Usage Audio:", bool(audio.usage_audio_url))
            print("Phonetic Script Audio:", bool(audio.phonetic_script_audio_url))
            print(
                "Syllabified Transcript Audio:",
                bool(audio.syllabified_stressed_transcript_audio_url)
            )
        else:
            print("WARNING: WordAudios record not found")

        response.append({

            "word_id": str(word.id),
            "word": word.word,

            # Existing fields
            "meaning": word.meaning,
            "part_of_speech": word.part_of_speech,
            "origin": word.origin,
            "usage": word.usage,
            "subject": word.subject,
            "concept": word.concept,
            "hint": word.hint,
            "difficulty": word.difficulty,

            # New word fields
            "root_word": word.root_word,
            "phonetic_script": word.phonetic_script,
            "syllabified_stressed_transcript": (
                word.syllabified_stressed_transcript
            ),
            "origin_word": word.origin_word or None,
            "origin_word_meaning": word.origin_word_meaning or None,
            "antonym": word.antonym or None,
            "synonym": word.synonym or None,
            "points": word.points,
            "word_status": word.word_status,
            "domain": word.domain,

            # Seven audio URLs
            "pronunciation_audio_url": (
                audio.pronunciation_audio_url if audio else None
            ),
            "meaning_audio_url": (
                audio.meaning_audio_url if audio else None
            ),
            "part_of_speech_audio_url": (
                audio.part_of_speech_audio_url if audio else None
            ),
            "origin_audio_url": (
                audio.origin_audio_url if audio else None
            ),
            "usage_audio_url": (
                audio.usage_audio_url if audio else None
            ),
            "phonetic_script_audio_url": (
                audio.phonetic_script_audio_url if audio else None
            ),
            "syllabified_stressed_transcript_audio_url": (
                audio.syllabified_stressed_transcript_audio_url
                if audio else None
            )
        })

    print("\n========== GET PRACTICE WORDS COMPLETED ==========")
    print("Final Response Word Count:", len(response))

    return response



def getReferralCode():
    return f"VR{random.randint(100000, 999999)}"

def import_word_from_schoolfirst(word_text):

    response = requests.get(
        "https://api.schoolfirst.ai/vocabee/api/word",
        params={
            "word": word_text
        },
        timeout=20
    )
    if response.status_code != 200:
        return None
    data = response.json()
    if data["success"]:
        return data["data"]
    else:
        return None