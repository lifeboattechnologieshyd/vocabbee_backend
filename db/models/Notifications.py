import uuid

from django.db import models

from db.models import AuditModel, UserMaster


class NotificationTemplate(AuditModel):

    CHANNELS = (
        ("PUSH", "PUSH"),
        ("EMAIL", "EMAIL"),
        ("SMS", "SMS"),
        ("WHATSAPP", "WHATSAPP"),
        ("IN_APP", "IN_APP"),
    )

    name = models.CharField(
        max_length=200
    )

    title = models.CharField(
        max_length=255
    )

    body = models.TextField()

    image = models.URLField(
        null=True,
        blank=True
    )

    payload = models.JSONField(
        default=dict,
        blank=True
    )

    channels = models.JSONField(
        default=list,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "notification_template"

    def __str__(self):
        return self.name


class NotificationCampaign(AuditModel):

    STATUS = (
        ("DRAFT", "DRAFT"),
        ("SENDING", "SENDING"),
        ("COMPLETED", "COMPLETED"),
        ("FAILED", "FAILED"),
        ("CANCELLED", "CANCELLED"),
    )

    AUDIENCE = (
        ("ALL_USERS", "ALL_USERS"),
        ("PARENTS", "PARENTS"),
        ("KIDS", "KIDS"),
        ("GRADES", "GRADES"),
        ("SPECIFIC_USERS", "SPECIFIC_USERS"),
        ("SPECIFIC_KIDS", "SPECIFIC_KIDS"),
        ("ACTIVE_USERS", "ACTIVE_USERS"),
        ("INACTIVE_USERS", "INACTIVE_USERS"),
    )

    title = models.CharField(
        max_length=255
    )

    body = models.TextField()

    image = models.URLField(
        null=True,
        blank=True
    )

    payload = models.JSONField(
        default=dict,
        blank=True
    )

    channels = models.JSONField(
        default=list,
        blank=True
    )

    audience = models.CharField(
        max_length=50,
        choices=AUDIENCE
    )

    grade_ids = models.JSONField(
        default=list,
        blank=True
    )

    user_ids = models.JSONField(
        default=list,
        blank=True
    )

    kid_ids = models.JSONField(
        default=list,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="DRAFT"
    )

    total_recipients = models.PositiveIntegerField(
        default=0
    )

    success_count = models.PositiveIntegerField(
        default=0
    )

    failed_count = models.PositiveIntegerField(
        default=0
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        UserMaster,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notifications_created"
    )
    class Meta:
        db_table = "notification_campaign"

    def __str__(self):
        return self.title


class NotificationRecipients(AuditModel):

    STATUS = (
        ("PENDING", "PENDING"),
        ("SENT", "SENT"),
        ("FAILED", "FAILED"),
        ("OPENED", "OPENED"),
    )

    CHANNELS = (
        ("PUSH", "PUSH"),
        ("EMAIL", "EMAIL"),
        ("SMS", "SMS"),
        ("WHATSAPP", "WHATSAPP"),
        ("IN_APP", "IN_APP"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    notification = models.ForeignKey(
        NotificationCampaign,
        on_delete=models.CASCADE,
        related_name="recipients"
    )

    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="notification_recipients"
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNELS
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING"
    )

    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    opened_at = models.DateTimeField(
        null=True,
        blank=True
    )
    class Meta:
        db_table = "notification_recipients"

    def __str__(self):
        return f"{self.notification} - {self.user}"