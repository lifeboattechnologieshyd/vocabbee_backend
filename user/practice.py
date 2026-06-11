# Practice Mode api's
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView

from db.models.user import PracticeAttempts, Words, PracticeAttemptAnswers, KidWordProgress
from shared.helper import get_practice_words
from shared.utils import CustomResponse


class StartPractice(APIView):

    def post(self, request):
        kid_id = request.data.get("kid_id")
        if not kid_id:
            return CustomResponse().errorResponse(
                data={},
                description="Kid ID is required"
            )
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).select_related(
            "grade"
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid kid"
            )

        attempt = PracticeAttempts.objects.create(
            kid=kid,
            started_at=timezone.now()
        )
        response = get_practice_words(kid)
        return CustomResponse().successResponse(
            data={
                "attempt_id": str(attempt.id),
                "total_questions": len(response),
                "words": response
            },
            description="Practice started successfully"
        )

class SubmitPracticeAnswer(APIView):

    @transaction.atomic
    def post(self, request):

        attempt_id = request.data.get(
            "attempt_id"
        )

        word_id = request.data.get(
            "word_id"
        )

        typed_answer = request.data.get(
            "typed_answer",
            ""
        ).strip()

        time_taken_seconds = request.data.get(
            "time_taken_seconds",
            0
        )

        is_last_question = request.data.get(
            "is_last_question",
            False
        )

        attempt = PracticeAttempts.objects.select_related(
            "kid"
        ).filter(
            id=attempt_id
        ).first()

        if not attempt:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid attempt"
            )

        word = Words.objects.filter(
            id=word_id,
            is_active=True
        ).first()

        if not word:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid word"
            )

        is_correct = (
            typed_answer.lower().strip()
            ==
            word.word.lower().strip()
        )

        PracticeAttemptAnswers.objects.create(
            attempt=attempt,
            word=word,
            typed_answer=typed_answer,
            is_correct=is_correct,
            time_taken_seconds=time_taken_seconds
        )

        progress, _ = KidWordProgress.objects.get_or_create(
            kid=attempt.kid,
            word=word,
            defaults={
                "times_seen": 0,
                "times_correct": 0
            }
        )

        progress.times_seen += 1

        if is_correct:
            progress.times_correct += 1

        progress.last_attempted_at = timezone.now()

        progress.save()

        attempt.total_questions += 1

        if is_correct:

            attempt.correct_answers += 1

            # score logic can evolve later
            attempt.score += 1

        else:

            attempt.wrong_answers += 1

        attempt.save()

        response = {
            "is_correct": is_correct,
            "correct_word": word.word
        }
        if is_last_question:
            next_words = get_practice_words(attempt.kid)
            response["next_words"] = next_words
        return CustomResponse().successResponse(
            data=response,
            description="Answer submitted successfully"
        )


class SkipPracticeQuestion(APIView):

    @transaction.atomic
    def post(self, request):

        attempt_id = request.data.get(
            "attempt_id"
        )

        word_id = request.data.get(
            "word_id"
        )

        time_taken_seconds = request.data.get(
            "time_taken_seconds",
            60
        )

        is_last_question = request.data.get(
            "is_last_question",
            False
        )

        attempt = PracticeAttempts.objects.select_related(
            "kid"
        ).filter(
            id=attempt_id
        ).first()

        if not attempt:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid attempt"
            )

        word = Words.objects.filter(
            id=word_id,
            is_active=True
        ).first()

        if not word:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid word"
            )

        PracticeAttemptAnswers.objects.create(
            attempt=attempt,
            word=word,
            is_skipped=True,
            time_taken_seconds=time_taken_seconds
        )

        progress, _ = KidWordProgress.objects.get_or_create(
            kid=attempt.kid,
            word=word,
            defaults={
                "times_seen": 0,
                "times_correct": 0
            }
        )

        progress.times_seen += 1
        progress.last_attempted_at = timezone.now()
        progress.save()
        attempt.total_questions += 1
        attempt.skipped_answers += 1
        attempt.save()
        response = {
            "is_skipped": True,
            "correct_word": word.word
        }
        if is_last_question:
            next_words = get_practice_words(attempt.kid)
            response["next_words"] = next_words
        return CustomResponse().successResponse(
            data=response,
            description="Question skipped successfully"
        )

class EndPractice(APIView):

    def post(self, request):

        attempt_id = request.data.get(
            "attempt_id"
        )

        if not attempt_id:
            return CustomResponse().errorResponse(
                data={},
                description="Attempt ID is required"
            )

        attempt = PracticeAttempts.objects.select_related(
            "kid"
        ).filter(
            id=attempt_id
        ).first()

        if not attempt:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid attempt"
            )

        if attempt.completed_at:

            return CustomResponse().successResponse(
                data={
                    "attempt_id": str(attempt.id),

                    "score": attempt.score,

                    "total_questions":
                        attempt.total_questions,

                    "correct_answers":
                        attempt.correct_answers,

                    "wrong_answers":
                        attempt.wrong_answers,

                    "skipped_answers":
                        attempt.skipped_answers,

                    "started_at":
                        attempt.started_at,

                    "completed_at":
                        attempt.completed_at
                },
                description="Practice already completed"
            )

        attempt.completed_at = timezone.now()

        attempt.save(
            update_fields=[
                "completed_at",
                "updated_at"
            ]
        )

        return CustomResponse().successResponse(
            data={
                "attempt_id": str(attempt.id),

                "score": attempt.score,

                "total_questions":
                    attempt.total_questions,

                "correct_answers":
                    attempt.correct_answers,

                "wrong_answers":
                    attempt.wrong_answers,

                "skipped_answers":
                    attempt.skipped_answers,

                "started_at":
                    attempt.started_at,

                "completed_at":
                    attempt.completed_at
            },
            description="Practice completed successfully"
        )


class PracticeStats(APIView):

    def get(self, request):

        kid_id = request.GET.get(
            "kid_id"
        )

        if not kid_id:
            return CustomResponse().errorResponse(
                data={},
                description="Kid ID is required"
            )

        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).select_related(
            "grade"
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid kid"
            )

        total_words_in_grade = Words.objects.filter(
            grade=kid.grade,
            is_active=True
        ).count()

        progress_queryset = KidWordProgress.objects.filter(
            kid=kid
        )

        attempted_words = progress_queryset.count()

        mastered_words = progress_queryset.filter(
            times_correct__gt=0
        ).count()

        weak_words = progress_queryset.filter(
            times_seen__gt=0,
            times_correct=0
        ).count()

        unseen_words = max(
            total_words_in_grade - attempted_words,
            0
        )

        completion_percentage = 0

        if total_words_in_grade:

            completion_percentage = round(
                (
                    attempted_words /
                    total_words_in_grade
                ) * 100,
                2
            )

        return CustomResponse().successResponse(
            data={
                "total_words_in_grade":
                    total_words_in_grade,

                "attempted_words":
                    attempted_words,

                "mastered_words":
                    mastered_words,

                "weak_words":
                    weak_words,

                "unseen_words":
                    unseen_words,

                "completion_percentage":
                    completion_percentage
            },
            description="Practice stats fetched successfully"
        )

class PracticeHistoryAPIView(APIView):

    def get(self, request):
        kid_id = request.GET.get(
            "kid_id"
        )
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid kid"
            )
        practice_attempts = PracticeAttempts.objects.filter(
            kid=kid
        ).values(
            "id",
            "total_questions",
            "correct_answers",
            "wrong_answers",
            "skipped_answers",
            "score",
            "started_at",
            "completed_at"
        ).order_by("-started_at")
        return CustomResponse().errorResponse(
                data=list(practice_attempts),
                description="Success"
            )
