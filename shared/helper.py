from db.models.user import KidWordProgress, Words, WordAudios
import random
import requests

#######################################
##
## this will be used to fetch and serve the questions
## in practice mode. used in start api, submit api and skip api.
##
######################################
def get_practice_words(kid,no_of_questions=10):
    attempted_word_ids = list(
        KidWordProgress.objects.filter(
            kid=kid
        ).values_list(
            "word_id",
            flat=True
        )
    )

    selected_words = list(
        Words.objects.filter(
            grade=kid.grade,
            is_active=True,
            voice_status='GENERATED',
            is_valid =True
        ).select_related(
            "audio"
        ).exclude(
            id__in=attempted_word_ids
        ).order_by("?")[:no_of_questions]
    )

    if len(selected_words) < no_of_questions:
        remaining_count = (
                no_of_questions - len(selected_words)
        )

        selected_word_ids = [
            word.id
            for word in selected_words
        ]

        additional_words = list(
            Words.objects.filter(
                grade=kid.grade,
                is_active=True,
                voice_status='GENERATED'
            ).select_related(
                "audio"
            ).exclude(
                id__in=selected_word_ids
            ).order_by("?")[:remaining_count]
        )

        selected_words.extend(
            additional_words
        )

    response = []

    for word in selected_words:
        response.append({
            "word_id": str(word.id),
            "word": str(word.word),
            "meaning": str(word.meaning),
            "part_of_speech": str(word.part_of_speech),
            "origin": str(word.origin),
            "usage": str(word.usage),
            "pronunciation_audio_url":
                word.audio.pronunciation_audio_url,
            "meaning_audio_url":
                word.audio.meaning_audio_url,
            "part_of_speech_audio_url":
                word.audio.part_of_speech_audio_url,
            "origin_audio_url":
                word.audio.origin_audio_url,
            "usage_audio_url":
                word.audio.usage_audio_url
        })
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