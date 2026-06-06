import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from crum import get_current_request


class TimeAuditModel(models.Model):
    """To path when the record was created and last modified"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Modified At")

    class Meta:
        abstract = True


class UserAuditModel(models.Model):
    """To path when the record was created and last modified"""

    created_by = models.CharField(
        max_length=255,
        verbose_name="Created By",
        null=True,
    )
    updated_by = models.CharField(
        max_length=255,
        verbose_name="Updated By",
        null=True,
    )

    class Meta:
        abstract = True


class AuditModel(TimeAuditModel, UserAuditModel):
    """To path when the record was created and last modified"""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        request = get_current_request()
        if request and hasattr(request, "user"):
            if not self.created_by:
                self.created_by = str(request.user.id)
            self.updated_by = str(request.user.id)

        super().save(*args, **kwargs)


class CustomUserManager(BaseUserManager):
    def create_user(self, mobile, password="password", **extra_fields):
        if not mobile:
            raise ValueError("The Mobile Number must be set")



        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class UserMaster(AbstractBaseUser):
    ROLE_CHOICES = (
        ("parent", "Parent"),
        ("admin", "Admin"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)], unique=True
    )
    full_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    profile_image = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    is_mobile_verified = models.BooleanField(default=False)
    user_role = ArrayField(models.CharField(
        max_length=50, ),
        default=list,
        blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(
        max_length=255,
        null=True,
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True
    )
    updated_by = models.CharField(
        max_length=255,
        null=True,
    )
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    coins = models.PositiveIntegerField(
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = []

    @property
    def is_admin(self):
        return "admin" in (self.user_role or [])

    @property
    def is_parent(self):
        return "parent" in (self.user_role or [])

    @property
    def display_name(self):
        return self.full_name or str(self.mobile)

    @property
    def is_profile_completed(self):
        return bool(self.full_name)


    class Meta:
        db_table = "user_master"

    def __str__(self):
        return str(self.mobile)

class Referrals(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    referrer = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="referrals_given"
    )

    referred_user = models.OneToOneField(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="referral_received"
    )

    referral_code = models.CharField(
        max_length=20
    )

    reward_coins = models.PositiveIntegerField(
        default=50
    )

    class Meta:
        db_table = "referrals"


class CoinTransactions(AuditModel):
    TXN_TYPES = (
        ("REFERRAL_BONUS", "REFERRAL_BONUS"),
        ("REFERRAL_JOIN_BONUS", "REFERRAL_JOIN_BONUS"),
        ("DAILY_STREAK", "DAILY_STREAK"),
        ("COMPETITION_REWARD", "COMPETITION_REWARD"),
        ("ADMIN_CREDIT", "ADMIN_CREDIT"),
        ("HINT_USAGE", "HINT_USAGE"),
        ("GAMEPLAY", "GAMEPLAY"),
        ("MEMBERSHIP_PURCHASE", "MEMBERSHIP_PURCHASE"),
    )
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="coin_transactions"
    )
    coins = models.IntegerField()
    transaction_type = models.CharField(
        max_length=50
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True
    )
    remarks = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    balance_after_transaction = models.PositiveIntegerField(
        default=0
    )
    class Meta:
        db_table = "coin_transactions"
        indexes = [
            models.Index(
                fields=["user"]
            ),
            models.Index(
                fields=["transaction_type"]
            )
        ]



class OTPs(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "otp"

class Grades(AuditModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=50
    )
    sort_order = models.IntegerField(
        default=1
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "grades"

class Kids(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    parent = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="kids"
    )

    grade = models.ForeignKey(
        Grades,
        on_delete=models.PROTECT,
        related_name="kids"
    )

    name = models.CharField(
        max_length=100
    )
    date_of_birth = models.DateField(null=True, blank=True)

    profile_image = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "kids"

class Words(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    grade = models.ForeignKey(
        Grades,
        on_delete=models.PROTECT,
        related_name="words"
    )

    word = models.CharField(
        max_length=255, unique=True
    )

    difficulty = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    meaning = models.TextField(
        blank=True,
        null=True
    )
    part_of_speech = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    origin = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    usage = models.TextField(
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "words"
        indexes = [
            models.Index(
                fields=["grade"]
            ),
            models.Index(
                fields=["difficulty"]
            ),
            models.Index(
                fields=["is_active"]
            ),
            models.Index(
                fields=["grade", "difficulty"]
            ),
            models.Index(
                fields=["grade", "is_active"]
            ),
            models.Index(
                fields=["word"]
            )
        ]

class WordAudios(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    word = models.OneToOneField(
        Words,
        on_delete=models.CASCADE,
        related_name="audio"
    )

    pronunciation_audio_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    meaning_audio_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    part_of_speech_audio_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    origin_audio_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    usage_audio_url = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    class Meta:
        db_table = "word_audios"


class DailyChallengeWords(AuditModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    challenge_date = models.DateField()
    grade = models.ForeignKey(
        Grades,
        on_delete=models.PROTECT
    )
    word = models.ForeignKey(
        Words,
        on_delete=models.PROTECT
    )

    order = models.IntegerField(
        default=1
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "daily_challenge_words"
        unique_together = (
            "challenge_date",
            "grade",
            "word"
        )


class KidWordProgress(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    kid = models.ForeignKey(
        Kids,
        on_delete=models.CASCADE,
        related_name="word_progress"
    )

    word = models.ForeignKey(
        Words,
        on_delete=models.CASCADE,
        related_name="kid_progress"
    )

    times_seen = models.PositiveIntegerField(
        default=0
    )

    times_correct = models.PositiveIntegerField(
        default=0
    )

    last_attempted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "kid_word_progress"

        unique_together = (
            "kid",
            "word"
        )

        indexes = [
            models.Index(
                fields=["kid"]
            ),
            models.Index(
                fields=["word"]
            ),
            models.Index(
                fields=["kid", "word"]
            )
        ]


class PracticeAttempts(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    kid = models.ForeignKey(
        Kids,
        on_delete=models.CASCADE,
        related_name="practice_attempts"
    )
    total_questions = models.PositiveIntegerField(
        default=10
    )
    skipped_answers = models.PositiveIntegerField(
        default=0
    )
    wrong_answers = models.PositiveIntegerField(
        default=0
    )
    correct_answers = models.PositiveIntegerField(
        default=0
    )
    score = models.PositiveIntegerField(
        default=0
    )
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    class Meta:
        db_table = "practice_attempts"


class PracticeAttemptAnswers(AuditModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    attempt = models.ForeignKey(
        PracticeAttempts,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    word = models.ForeignKey(
        Words,
        on_delete=models.PROTECT
    )

    typed_answer = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    is_correct = models.BooleanField(
        default=False
    )

    is_skipped = models.BooleanField(
        default=False
    )

    time_taken_seconds = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        db_table = "practice_attempt_answers"