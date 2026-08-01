from django.core.paginator import Paginator
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.firebase import send_visible_push_notification, send_bulk_push_notification
from db.models import Grades, Words, UserMaster, Devices
from db.models.compete import Tournaments, TournamentGrades, TournamentQuestions, TournamentParticipants
from shared.utils import CustomResponse


class TournamentCreateAPIView(APIView):

    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = request.data
        title = data.get("title")
        description = data.get("description")
        tournament_type = data.get("tournament_type")
        total_questions = data.get("total_questions")
        duration_minutes = data.get("duration_minutes")
        start_at = data.get("start_at")
        end_at = data.get("end_at")
        max_participants = data.get("max_participants")
        entry_fee = data.get("entry_fee", 0)
        prize_pool = data.get("prize_pool", 0)

        if not title:
            return CustomResponse().errorResponse(
                description="Tournament title is required."
            )

        if not tournament_type:
            return CustomResponse().errorResponse(
                description="Tournament type is required."
            )

        if not total_questions:
            return CustomResponse().errorResponse(
                description="Total questions is required."
            )

        if not duration_minutes:
            return CustomResponse().errorResponse(
                description="Duration is required."
            )

        if not start_at:
            return CustomResponse().errorResponse(
                description="Start date & time is required."
            )

        if not end_at:
            return CustomResponse().errorResponse(
                description="End date & time is required."
            )

        # if Tournaments.objects.filter(
        #     title__iexact=title.strip()
        # ).exists():
        #     return CustomResponse().errorResponse(
        #         description="Tournament with this title already exists."
        #     )

        subject = None

        # if subject_id:
        #
        #     subject = Subjects.objects.filter(
        #         id=subject_id
        #     ).first()
        #
        #     if not subject:
        #         return CustomResponse().errorResponse(
        #             description="Invalid subject."
        #         )

        tournament = Tournaments.objects.create(
            title=title.strip(),
            description=description,
            tournament_type=tournament_type,
            subject=subject,
            total_questions=total_questions,
            duration_minutes=duration_minutes,
            start_at=start_at,
            end_at=end_at,
            max_participants=max_participants,
            entry_fee=entry_fee,
            prize_pool=prize_pool,
            status="DRAFT"
        )

        return CustomResponse().successResponse(
            data={
                "id": str(tournament.id)
            },
            description="Tournament created successfully."
        )

    def get(self, request):

        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        status = request.GET.get("status")
        tournament_type = request.GET.get("tournament_type")
        subject_id = request.GET.get("subject_id")
        search = request.GET.get("search")

        tournaments = Tournaments.objects.annotate(
            participant_count=Count("participants", distinct=True),
            grade_count=Count("eligible_grades", distinct=True),
            question_count=Count("questions", distinct=True)
        ).order_by("-created_at")

        if status:
            tournaments = tournaments.filter(status=status)

        if tournament_type:
            tournaments = tournaments.filter(
                tournament_type=tournament_type
            )

        if subject_id:
            tournaments = tournaments.filter(
                subject_id=subject_id
            )

        if search:
            tournaments = tournaments.filter(
                title__icontains=search
            )

        paginator = Paginator(
            tournaments,
            page_size
        )

        page_obj = paginator.get_page(page)

        data = []

        for tournament in page_obj:

            data.append({
                "id": str(tournament.id),
                "title": tournament.title,
                "subject": tournament.subject.name if tournament.subject else "",
                "tournament_type": tournament.tournament_type,
                "status": tournament.status,
                "total_questions": tournament.total_questions,
                "assigned_questions": tournament.question_count,
                "eligible_grades": tournament.grade_count,
                "participants": tournament.participant_count,
                "start_at": tournament.start_at,
                "end_at": tournament.end_at
            })

        return CustomResponse().successResponse(
            data={
                "current_page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_records": paginator.count,
                "results": data
            }
        )

class TournamentDetailsAPIView(APIView):

    def get(self, request, tournament_id):

        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()

        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )

        grades = []

        tournament_grades = TournamentGrades.objects.filter(
            tournament=tournament
        ).select_related("grade")

        for item in tournament_grades:
            grades.append({
                "id": str(item.grade.id),
                "name": item.grade.name
            })

        words = []

        tournament_questions = TournamentQuestions.objects.filter(
            tournament=tournament
        ).select_related("word").order_by("display_order")

        for item in tournament_questions:
            words.append({
                "tournament_question_id": str(item.id),
                "word_id": str(item.word.id),
                "display_order": item.display_order,
                "word": item.word.word
            })

        participant_count = TournamentParticipants.objects.filter(
            tournament=tournament
        ).count()

        return CustomResponse().successResponse(
            data={
                "id": str(tournament.id),
                "title": tournament.title,
                "description": tournament.description,
                "tournament_type": tournament.tournament_type,
                "status": tournament.status,
                "total_questions": tournament.total_questions,
                "duration_minutes": tournament.duration_minutes,
                "start_at": tournament.start_at,
                "end_at": tournament.end_at,
                "max_participants": tournament.max_participants,
                "entry_fee": tournament.entry_fee,
                "prize_pool": tournament.prize_pool,

                "total_grades": len(grades),
                "total_words": len(words),
                "total_participants": participant_count,

                "grades": grades,
                "words": words
            },
            description="Tournament details fetched successfully."
        )


class TournamentAssignGradesAPIView(APIView):

    def post(self, request, tournament_id):
        data = request.data
        grade_ids = data.get("grades", [])
        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        if tournament.status != "DRAFT":
            return CustomResponse().errorResponse(
                description="Grades can only be updated while the tournament is in Draft status."
            )
        if not isinstance(grade_ids, list):
            return CustomResponse().errorResponse(
                description="Grades should be a list."
            )
        grades = Grades.objects.filter(
            id__in=grade_ids,
            is_active=True
        )
        if grades.count() != len(set(grade_ids)):
            return CustomResponse().errorResponse(
                description="One or more selected grades are invalid."
            )
        TournamentGrades.objects.filter(
            tournament=tournament
        ).delete()
        mappings = []
        for grade in grades:
            mappings.append(
                TournamentGrades(
                    tournament=tournament,
                    grade=grade
                )
            )
        TournamentGrades.objects.bulk_create(mappings)
        return CustomResponse().successResponse(
            data={
                "total_grades": len(mappings)
            },
            description="Grades assigned successfully."
        )


class TournamentAvailableWordsAPIView(APIView):

    def post(self, request):
        page = int(request.data.get("page", 1))
        page_size = int(request.data.get("page_size", 20))
        search = request.data.get("search")
        grade_ids = request.data.get("grade_ids")
        # difficulty_levels = request.data.getlist("difficulty_levels")
        words = Words.objects.filter(
            is_active=True,
            voice_status='GENERATED',
        ).select_related(
            "grade",
        ).order_by(
            "word"
        )
        if search:
            words = words.filter(
                word__icontains=search
            )
        if grade_ids:
            words = words.filter(
                grade_id__in=grade_ids
            )
        paginator = Paginator(words, page_size)
        page_obj = paginator.get_page(page)
        results = []
        for word in page_obj:
            results.append({
                "id": str(word.id),
                "word": word.word,
                "grade": {
                    "id": str(word.grade.id),
                    "name": word.grade.name
                } if word.grade else None,
            })
        return CustomResponse().successResponse(
            data={
                "current_page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_records": paginator.count,
                "results": results
            },
            description="Words fetched successfully."
        )

class TournamentAssignQuestionsAPIView(APIView):

    def post(self, request, tournament_id):

        data = request.data
        words = data.get("words", [])
        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        if tournament.status != "DRAFT":
            return CustomResponse().errorResponse(
                description="Questions can only be updated while the tournament is in Draft status."
            )
        if not isinstance(words, list):
            return CustomResponse().errorResponse(
                description="Words should be a list."
            )
        if len(words) == 0:
            return CustomResponse().errorResponse(
                description="Please select at least one word."
            )
        word_ids = [item.get("word_id") for item in words]
        db_words = Words.objects.filter(
            id__in=word_ids,
            is_active=True
        )
        if db_words.count() != len(set(word_ids)):
            return CustomResponse().errorResponse(
                description="One or more selected words are invalid."
            )
        if len(words) != tournament.total_questions:
            return CustomResponse().errorResponse(
                description=f"Please assign exactly {tournament.total_questions} questions."
            )
        word_map = {}
        for word in db_words:
            word_map[str(word.id)] = word
        TournamentQuestions.objects.filter(
            tournament=tournament
        ).delete()
        mappings = []
        for item in words:
            word = word_map.get(item.get("word_id"))
            if not word:
                continue
            mappings.append(
                TournamentQuestions(
                    tournament=tournament,
                    word=word,
                    display_order=item.get("display_order")
                )
            )
        TournamentQuestions.objects.bulk_create(mappings)
        return CustomResponse().successResponse(
            data={
                "total_questions": len(mappings)
            },
            description="Questions assigned successfully."
        )

class TournamentPublishAPIView(APIView):

    def post(self, request, tournament_id):

        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()

        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )

        if tournament.status != "DRAFT":
            return CustomResponse().errorResponse(
                description="Only Draft tournaments can be published."
            )

        grades_count = TournamentGrades.objects.filter(
            tournament=tournament
        ).count()

        if grades_count == 0:
            return CustomResponse().errorResponse(
                description="Please assign at least one grade."
            )

        questions_count = TournamentQuestions.objects.filter(
            tournament=tournament
        ).count()

        if questions_count != tournament.total_questions:
            return CustomResponse().errorResponse(
                description=f"Please assign exactly {tournament.total_questions} questions."
            )

        if tournament.start_at >= tournament.end_at:
            return CustomResponse().errorResponse(
                description="End date & time should be greater than start date & time."
            )
        tournament.status = "UPCOMING"
        tournament.save()
        TournyReminders.tourney_active(tournament)
        return CustomResponse().successResponse(
            data={},
            description="Tournament published successfully."
        )

class TournamentCancelAPIView(APIView):

    def post(self, request, tournament_id):

        tournament = Tournaments.objects.filter(
            id=tournament_id
        ).first()
        if not tournament:
            return CustomResponse().errorResponse(
                description="Tournament not found."
            )
        if tournament.status == "CANCELLED":
            return CustomResponse().errorResponse(
                description="Tournament is already cancelled."
            )
        if tournament.status == "COMPLETED":
            return CustomResponse().errorResponse(
                description="Completed tournaments cannot be cancelled."
            )
        if tournament.status == "LIVE":
            return CustomResponse().errorResponse(
                description="Live tournaments cannot be cancelled."
            )
        tournament.status = "CANCELLED"
        tournament.save()
        return CustomResponse().successResponse(
            data={},
            description="Tournament cancelled successfully."
        )


class TournyReminders:
    @classmethod
    def tourney_active(cls, tournament):
        eligible_grade_ids = TournamentGrades.objects.filter(
            tournament=tournament
        ).values_list(
            "grade_id",
            flat=True
        )
        user_ids = UserMaster.objects.filter(
            kids__grade_id__in=eligible_grade_ids,
        ).distinct().values_list(
            "id",
            flat=True
        )
        tokens = Devices.objects.filter(
            user_id__in=user_ids,
            is_active=True
        ).exclude(
            fcm_token=""
        ).values_list(
            "fcm_token",
            flat=True
        )
        tokens = set(tokens)
        pushinfo = send_bulk_push_notification(tokens,
                                              "🏆 New Tournament Published",
                                              f"{tournament.title} is now open for registration.",
                                              {
                                                  "tournament_id": tournament.id
                                              },
                                               "TOURNEY_PUBLISH",
                                               )
        print(pushinfo)