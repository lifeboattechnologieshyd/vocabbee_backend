import uuid

from db.models import AuditModel, Subjects, Grades, Words, Kids
from django.db import models


class Tournaments(AuditModel):

    STATUS = (
        ("DRAFT", "DRAFT"),
        ("UPCOMING", "UPCOMING"),
        ("LIVE", "LIVE"),
        ("COMPLETED", "COMPLETED"),
        ("CANCELLED", "CANCELLED"),
    )

    TYPE = (
        ("DAILY", "DAILY"),
        ("WEEKLY", "WEEKLY"),
        ("SPECIAL", "SPECIAL"),
        ("SCHOOL", "SCHOOL"),
        ("STATE", "STATE"),
        ("NATIONAL", "NATIONAL"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    title = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True
    )

    tournament_type = models.CharField(
        max_length=20,
        choices=TYPE
    )

    subject = models.ForeignKey(
        Subjects,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    total_questions = models.PositiveIntegerField(default=50)

    duration_minutes = models.PositiveIntegerField(default=30)

    start_at = models.DateTimeField()

    end_at = models.DateTimeField()

    max_participants = models.PositiveIntegerField(default=0)

    entry_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    prize_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="DRAFT"
    )

    class Meta:
        db_table = "tournaments"


class TournamentGrades(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    tournament = models.ForeignKey(
        Tournaments,
        on_delete=models.CASCADE,
        related_name="eligible_grades"
    )

    grade = models.ForeignKey(
        Grades,
        on_delete=models.CASCADE
    )

    class Meta:
        db_table = "tournament_grades"
        unique_together = (
            "tournament",
            "grade"
        )

class TournamentQuestions(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    tournament = models.ForeignKey(
        Tournaments,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    word = models.ForeignKey(
        Words,
        on_delete=models.PROTECT
    )

    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "tournament_questions"

        unique_together = (
            "tournament",
            "display_order"
        )

class TournamentParticipants(AuditModel):

    STATUS = (
        ("JOINED", "JOINED"),
        ("STARTED", "STARTED"),
        ("COMPLETED", "COMPLETED"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    tournament = models.ForeignKey(
        Tournaments,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    kid = models.ForeignKey(
        Kids,
        on_delete=models.CASCADE
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(
        blank=True,
        null=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    attempted_questions = models.PositiveIntegerField(default=0)

    correct_answers = models.PositiveIntegerField(default=0)

    wrong_answers = models.PositiveIntegerField(default=0)

    skipped_answers = models.PositiveIntegerField(default=0)

    bonus_points = models.PositiveIntegerField(default=0)

    total_points = models.PositiveIntegerField(default=0)

    time_taken_seconds = models.PositiveIntegerField(default=0)

    rank = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="JOINED"
    )

    class Meta:
        db_table = "tournament_participants"

        unique_together = (
            "tournament",
            "kid"
        )

class TournamentAnswers(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    participant = models.ForeignKey(
        TournamentParticipants,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    tournament_question = models.ForeignKey(
        TournamentQuestions,
        on_delete=models.CASCADE
    )

    typed_answer = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    is_correct = models.BooleanField(default=False)

    points = models.PositiveIntegerField(default=0)

    time_taken_seconds = models.PositiveIntegerField(default=0)

    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tournament_answers"

        unique_together = (
            "participant",
            "tournament_question"
        )

class TournamentRewards(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tournament = models.ForeignKey(
        Tournaments,
        on_delete=models.CASCADE,
        related_name="rewards"
    )
    from_rank = models.PositiveIntegerField()
    to_rank = models.PositiveIntegerField()
    reward_points = models.PositiveIntegerField(default=0)
    reward_title = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    class Meta:
        db_table = "tournament_rewards"