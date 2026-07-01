from django.db.models import Count
from django.utils import timezone

from backoffice.notifications.engine import NotificationEngine
from db.models import NotificationRecipients



class CampaignDispatcher:

    @classmethod
    def process(cls, campaign):
        campaign.status = "PROCESSING"
        campaign.save(
            update_fields=["status"]
        )
        recipients = NotificationRecipients.objects.filter(
            notification=campaign,
            status="PENDING"
        )
        for recipient in recipients:
            NotificationEngine.process_recipient(
                recipient
            )
        summary = NotificationRecipients.objects.filter(
            notification=campaign
        ).values(
            "status"
        ).annotate(
            total=Count("id")
        )
        success = 0
        failed = 0
        for row in summary:
            if row["status"] == "SENT":
                success = row["total"]
            elif row["status"] == "FAILED":
                failed = row["total"]
        campaign.success_count = success
        campaign.failed_count = failed
        campaign.status = "COMPLETED"
        campaign.sent_at = timezone.now()
        campaign.save(
            update_fields=[
                "success_count",
                "failed_count",
                "status",
                "sent_at"
            ]
        )
        return True