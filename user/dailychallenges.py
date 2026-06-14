from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.models import DailyChallengeWords
from db.models.user import DailyChallengeAttempts, Kids, DailyChallengeAttemptAnswers, WordAudios
from shared.utils import CustomResponse


class DailyChallengesAPIView(APIView):

    permission_classes = [AllowAny]
    def get(self, request):
        kid = Kids.objects.get(
            id=request.GET.get("kid_id")
        )
        page = int(request.GET.get("page",1))
        challenge_dates = DailyChallengeWords.objects.filter(
            grade=kid.grade,
            is_active=True
        ).values_list(
            "challenge_date",
            flat=True
        ).distinct().order_by(
            "-challenge_date"
        )
        start_index = (page - 1) * 30
        end_index = (start_index + 30)
        challenge_dates = challenge_dates[start_index:end_index]
        today = timezone.localdate()
        results = []
        attempts = {
            attempt.challenge_date: attempt
            for attempt in DailyChallengeAttempts.objects.filter(
                kid=kid,
                challenge_date__in=challenge_dates
            )
        }
        for challenge_date in challenge_dates:
            attempt = attempts.get(
                challenge_date
            )
            if attempt:
                if attempt.status == "COMPLETED":
                    challenge_status = "COMPLETED"
                else:
                    challenge_status = "IN_PROGRESS"
            else:
                if challenge_date < today:
                    challenge_status = "MISSED"
                else:
                    challenge_status = "NOT_STARTED"
            results.append(
                {
                    "date": challenge_date,
                    "is_today": challenge_date == today,
                    "status": challenge_status
                }
            )
        return CustomResponse.successResponse(data=results,
                                                  description="")

class DailyChallengeWordsAPIView(APIView):

    def post(self, request):
        kid_id = request.data.get("kid_id")
        challenge_date = request.data.get("challenge_date")
        if not kid_id:
            return CustomResponse.errorResponse(
                description="kid_id is required"
            )
        if not challenge_date:
            return CustomResponse.errorResponse(
                description="challenge_date is required"
            )
        try:
            kid = Kids.objects.select_related(
                "grade"
            ).get(
                id=kid_id
            )
        except Kids.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Kid not found"
            )
        attempt, created = DailyChallengeAttempts.objects.get_or_create(
            kid=kid,
            challenge_date=challenge_date,
            defaults={
                "grade": kid.grade,
                "status": "IN_PROGRESS"
            }
        )
        attempted_word_ids = DailyChallengeAttemptAnswers.objects.filter(
            attempt=attempt
        ).values_list(
            "word_id",
            flat=True
        )

        challenge_words = (
            DailyChallengeWords.objects
            .filter(
                challenge_date=challenge_date,
                grade=kid.grade,
                is_active=True
            )
            .exclude(
                word_id__in=attempted_word_ids
            )
            .select_related(
                "word",
                "word__audio"
            )
            .order_by(
                "order"
            )
        )
        words = []
        for challenge_word in challenge_words:
            word = challenge_word.word
            try:
                audio = word.audio
            except WordAudios.DoesNotExist:
                audio = None
            words.append(
                {
                    "id": str(word.id),
                    "word": word.word,
                    "subject": word.subject,
                    "concept": word.concept,
                    "hint": word.hint,
                    "difficulty": word.difficulty,
                    "meaning": word.meaning,
                    "part_of_speech": word.part_of_speech,
                    "origin": word.origin,
                    "usage": word.usage,
                    "audios": {
                        "pronunciation_audio_url": (
                            audio.pronunciation_audio_url
                            if audio else None
                        ),
                        "meaning_audio_url": (
                            audio.meaning_audio_url
                            if audio else None
                        ),
                        "part_of_speech_audio_url": (
                            audio.part_of_speech_audio_url
                            if audio else None
                        ),
                        "origin_audio_url": (
                            audio.origin_audio_url
                            if audio else None
                        ),
                        "usage_audio_url": (
                            audio.usage_audio_url
                            if audio else None
                        )
                    }
                }
            )
        total_words = 10
        attempted_words = len(
            attempted_word_ids
        )
        remaining_words = len(
            words
        )
        return CustomResponse.successResponse(
            data={
                "attempt_id": str(attempt.id),
                "challenge_date": challenge_date,
                "status": attempt.status,
                "total_words": total_words,
                "attempted_words": attempted_words,
                "remaining_words": remaining_words,
                "words": words
            },
            description="Daily challenge words fetched successfully"
        )