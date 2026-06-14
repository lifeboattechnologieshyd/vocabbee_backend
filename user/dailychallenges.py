from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.models import DailyChallengeWords
from db.models.user import DailyChallengeAttempts, Kids
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
class GetWords(APIView):

    def get(self, request):
        pass