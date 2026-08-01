from django.db.models import Count
from django.utils import timezone
from rest_framework.views import APIView

from db.models.compete import TournamentParticipants, Tournaments, TournamentGrades, TournamentQuestions, \
    TournamentAnswers
from shared.utils import CustomResponse


class TournamentListAPIView(APIView):

    def get(self, request):
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        tournaments = Tournaments.objects.filter(
            status__in=[
                "UPCOMING",
                "LIVE"
            ],
            eligible_grades__grade=kid.grade
        ).distinct().annotate(
            participant_count=Count("participants", distinct=True)
        ).order_by(
            "start_at"
        )

        joined_tournament_ids = TournamentParticipants.objects.filter(
            kid=kid,
            tournament__in=tournaments
        ).values_list(
            "tournament_id",
            flat=True
        )
        joined_tournament_ids = set(joined_tournament_ids)
        data = []



        for tournament in tournaments:

            participant = TournamentParticipants.objects.filter(
                tournament=tournament,
                kid=kid
            ).first()
            participation_status = "NOT_JOINED"
            if participant:
                participation_status = participant.status

            data.append({
                "id": str(tournament.id),
                "title": tournament.title,
                "description": tournament.description,
                "tournament_type": tournament.tournament_type,
                "status": tournament.status,
                "participation_status": participation_status,
                "total_questions": tournament.total_questions,
                "duration_minutes": tournament.duration_minutes,
                "entry_fee": tournament.entry_fee,
                "prize_pool": tournament.prize_pool,
                "start_at": tournament.start_at,
                "end_at": tournament.end_at,
                "participants": tournament.participant_count,
                "is_joined": tournament.id in joined_tournament_ids
            })
        return CustomResponse().successResponse(
            data=data,
            description="Tournaments fetched successfully."
        )

class TournamentJoinAPIView(APIView):

    def post(self, request, tournament_id):
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        if tournament.status != "UPCOMING":
            return CustomResponse().errorResponse(
                description="Tournament is not open for joining."
            )
        is_eligible = TournamentGrades.objects.filter(
            tournament=tournament,
            grade=kid.grade
        ).exists()
        if not is_eligible:
            return CustomResponse().errorResponse(
                description="You are not eligible to join this tournament."
            )
        if TournamentParticipants.objects.filter(
            tournament=tournament,
            kid=kid
        ).exists():
            return CustomResponse().errorResponse(
                description="You have already joined this tournament."
            )
        participants_count = TournamentParticipants.objects.filter(
            tournament=tournament
        ).count()
        if (
            tournament.max_participants and
            participants_count >= tournament.max_participants
        ):
            return CustomResponse().errorResponse(
                description="Tournament is full."
            )
        participant = TournamentParticipants.objects.create(
            tournament=tournament,
            kid=kid,
            status="JOINED"
        )
        return CustomResponse().successResponse(
            data={
                "participant_id": str(participant.id),
                "joined_at": participant.joined_at
            },
            description="Tournament joined successfully."
        )

class TournamentStartAPIView(APIView):

    def post(self, request, tournament_id):
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        if tournament.status != "LIVE":
            return CustomResponse().errorResponse(
                description="Tournament is not live."
            )
        participant = TournamentParticipants.objects.filter(
            tournament=tournament,
            kid=kid
        ).first()
        if not participant:
            return CustomResponse().errorResponse(
                description="Please join the tournament first."
            )
        if participant.status == "COMPLETED":
            return CustomResponse().errorResponse(
                description="Tournament already completed."
            )

        if not participant.started_at:
            participant.started_at = timezone.now()
            participant.status = "STARTED"
            participant.save()

        answered_question_ids = TournamentAnswers.objects.filter(
            participant=participant
        ).values_list(
            "tournament_question_id",
            flat=True
        )

        question = TournamentQuestions.objects.filter(
            tournament=tournament,
            word__is_valid=True,
        ).exclude(
            id__in=answered_question_ids
        ).select_related(
            "word",
        ).order_by(
            "display_order"
        ).first()

        if not question:
            return CustomResponse().errorResponse(
                description="No questions found."
            )
        print(f"start api response == first word is {str(question.word.word)}")
        return CustomResponse().successResponse(
            data={
                "participant_id": str(participant.id),
                "remaining_time": tournament.duration_minutes * 60,
                "question": {
                    "question_id": str(question.id),
                    "question_no": question.display_order,
                    "total_questions": tournament.total_questions,
                    "word": {
                        "word_id": str(question.word.id),
                        "word": str(question.word.word),
                        "meaning": str(question.word.meaning),
                        "part_of_speech": str(question.word.part_of_speech),
                        "origin": str(question.word.origin),
                        "usage": str(question.word.usage),
                        "pronunciation_audio_url": question.word.audio.pronunciation_audio_url,
                        "meaning_audio_url":question.word.audio.meaning_audio_url,
                        "part_of_speech_audio_url":question.word.audio.part_of_speech_audio_url,
                        "origin_audio_url":question.word.audio.origin_audio_url,
                        "usage_audio_url":question.word.audio.usage_audio_url
                    },
                }
            },
            description="Tournament started successfully."
        )

class TournamentSubmitAnswerAPIView(APIView):

    def post(self, request, tournament_id):
        print(f"submit ans api request with payload ===> {request.data}")
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        data = request.data
        question_id = data.get("question_id")
        answer = data.get("answer", "").strip()
        time_taken = data.get("time_taken_seconds", 0)
        tournament = Tournaments.objects.filter(
            id=tournament_id,
            status="LIVE"
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        participant = TournamentParticipants.objects.filter(
            tournament=tournament,
            kid=kid,
            status="STARTED"
        ).first()
        if not participant:
            return CustomResponse().errorResponse(
                description="Tournament has not been started."
            )
        question = TournamentQuestions.objects.select_related(
            "word"
        ).filter(
            id=question_id,
            tournament=tournament
        ).first()
        if not question:
            return CustomResponse().errorResponse(
                description="Question not found."
            )
        if TournamentAnswers.objects.filter(
            participant=participant,
            tournament_question=question
        ).exists():
            return CustomResponse().errorResponse(
                description="Question already answered."
            )
        print(f"actual word is  ===> {question.word.word.strip().lower()}")
        print(f"entered word is  ===> {answer.lower()}")
        correct_answer = question.word.word.strip().lower()
        is_correct = answer.lower() == correct_answer
        points = 10 if is_correct else 0
        TournamentAnswers.objects.create(
            participant=participant,
            tournament_question=question,
            typed_answer=answer,
            is_correct=is_correct,
            points=points,
            time_taken_seconds=time_taken
        )
        participant.attempted_questions += 1
        participant.time_taken_seconds += time_taken
        participant.total_points += points
        if is_correct:
            participant.correct_answers += 1
        else:
            participant.wrong_answers += 1
        participant.save()
        next_question = TournamentQuestions.objects.filter(
            tournament=tournament,
            display_order=question.display_order + 1
        ).select_related(
            "word",
            "word__audio"
        ).first()
        if not next_question:
            participant.status = "COMPLETED"
            participant.completed_at = timezone.now()
            participant.save()
            return CustomResponse().successResponse(
                data={
                    "completed": True,
                    "is_correct": is_correct,
                    "score": participant.total_points,
                    "correct_answers": participant.correct_answers,
                    "wrong_answers": participant.wrong_answers
                },
                description="Tournament completed successfully."
            )
        print(f"Next word is === {str(next_question.word.word)}")
        return CustomResponse().successResponse(
            data={
                "completed": False,
                "score": participant.total_points,
                "is_correct": is_correct,
                "question": {
                    "question_id": str(next_question.id),
                    "question_no": next_question.display_order,
                    "total_questions": tournament.total_questions,
                    "word": {
                        "word_id": str(next_question.word.id),
                        "word": str(next_question.word.word),
                        "meaning": str(next_question.word.meaning),
                        "part_of_speech": str(next_question.word.part_of_speech),
                        "origin": str(next_question.word.origin),
                        "usage": str(next_question.word.usage),
                        "pronunciation_audio_url": next_question.word.audio.pronunciation_audio_url,
                        "meaning_audio_url":next_question.word.audio.meaning_audio_url,
                        "part_of_speech_audio_url":next_question.word.audio.part_of_speech_audio_url,
                        "origin_audio_url":next_question.word.audio.origin_audio_url,
                        "usage_audio_url":next_question.word.audio.usage_audio_url
                    },
                }
            },
            description="Answer submitted successfully."
        )


class TournamentLeaderboardAPIView(APIView):

    def get(self, request, tournament_id):
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        participants = TournamentParticipants.objects.filter(
            tournament=tournament
        ).select_related(
            "kid"
        ).order_by(
            "-total_points",
            "time_taken_seconds",
            "completed_at"
        )

        leaderboard = []

        my_rank = None

        for rank, participant in enumerate(participants, start=1):

            if participant.kid_id == kid.id:
                my_rank = rank

            leaderboard.append({
                "id": participant.id,
                "rank": rank,
                "kid_id": str(participant.kid.id),
                "name": participant.kid.name,
                "profile_picture": participant.kid.profile_image if participant.kid.profile_image else "",
                "score": participant.total_points,
                "correct_answers": participant.correct_answers,
                "time_taken_seconds": participant.time_taken_seconds
            })

        return CustomResponse().successResponse(
            data={
                "my_rank": my_rank,
                "leaderboard": leaderboard[:100]
            },
            description="Leaderboard fetched successfully."
        )

class TournamentResultAPIView(APIView):

    def get(self, request, tournament_id):
        kid_id = request.GET.get("kid_id")
        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()
        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )
        participant = TournamentParticipants.objects.filter(
            tournament_id=tournament_id,
            kid=kid
        ).first()
        if not participant:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        leaderboard = TournamentParticipants.objects.filter(
            tournament_id=tournament_id
        ).order_by(
            "-total_points",
            "time_taken_seconds",
            "completed_at"
        )
        rank = 1
        for item in leaderboard:
            if item.id == participant.id:
                break
            rank += 1
        return CustomResponse().successResponse(
            data={
                "rank": rank,
                "score": participant.total_points,
                "correct_answers": participant.correct_answers,
                "wrong_answers": participant.wrong_answers,
                "attempted_questions": participant.attempted_questions,
                "time_taken_seconds": participant.time_taken_seconds,
                "completed_at": participant.completed_at
            },
            description="Tournament result fetched successfully."
        )


from django.core.paginator import Paginator

class TournamentHistoryAPIView(APIView):

    def get(self, request):

        kid_id = request.GET.get("kid_id")

        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                description="Kid not found."
            )

        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        status = request.GET.get("status")
        search = request.GET.get("search")

        participants = TournamentParticipants.objects.filter(
            kid=kid
        ).select_related(
            "tournament"
        ).order_by(
            "-created_at"
        )

        if status:
            participants = participants.filter(
                tournament__status=status
            )

        if search:
            participants = participants.filter(
                tournament__title__icontains=search
            )

        paginator = Paginator(
            participants,
            page_size
        )

        page_obj = paginator.get_page(page)

        results = []

        for participant in page_obj:

            tournament = participant.tournament
            if tournament.status == 'UPCOMING':
                continue

            results.append({
                "tournament_id": str(tournament.id),
                "title": tournament.title,
                "tournament_type": tournament.tournament_type,
                "status": tournament.status,
                "score": participant.total_points,
                "rank": participant.rank,
                "correct_answers": participant.correct_answers,
                "wrong_answers": participant.wrong_answers,
                "attempted_questions": participant.attempted_questions,
                "time_taken_seconds": participant.time_taken_seconds,
                "completed_at": participant.completed_at
            })

        return CustomResponse().successResponse(
            data={
                "current_page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_records": paginator.count,
                "results": results
            },
            description="Tournament history fetched successfully."
        )


class TournamentAnswersAPIView(APIView):

    def get(self, request):
        participant_id = request.GET.get("participant_id")
        participant = TournamentParticipants.objects.filter(
            id=participant_id
        ).first()
        if not participant:
            return CustomResponse().errorResponse(
                description="Participant not found."
            )
        answers = (
            TournamentAnswers.objects
            .filter(
                participant=participant
            )
            .select_related(
                "tournament_question__word",
                "tournament_question__word__audio"
            )
            .order_by(
                "tournament_question__display_order"
            )
        )
        data = []
        for answer in answers:
            word = answer.tournament_question.word
            audio = getattr(word, "audio", None)
            data.append({
                "question_no": answer.tournament_question.display_order,
                "word_id": str(word.id),
                "actual_word": word.word,
                "typed_answer": answer.typed_answer,
                "is_correct": answer.is_correct,
                "meaning": word.meaning,
                "part_of_speech": word.part_of_speech,
                "origin": word.origin,
                "usage": word.usage,
                "pronunciation_audio_url": audio.pronunciation_audio_url if audio else None,
                "meaning_audio_url": audio.meaning_audio_url if audio else None,
                "part_of_speech_audio_url": audio.part_of_speech_audio_url if audio else None,
                "origin_audio_url": audio.origin_audio_url if audio else None,
                "usage_audio_url": audio.usage_audio_url if audio else None,
            })
        return CustomResponse().successResponse(
            data=data,
            description="Answers fetched successfully."
        )