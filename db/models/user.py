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


    class Meta:
        db_table = "user_master"

    def __str__(self):
        return str(self.mobile)

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
        max_length=255
    )

    difficulty = models.PositiveSmallIntegerField(
        default=1
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