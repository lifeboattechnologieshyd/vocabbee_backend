from backoffice.notifications.recipient_resolver import RecipientResolver
from db.models import NotificationRecipients


class CampaignQueueBuilder:

    @classmethod
    def build(cls, campaign):
        users = RecipientResolver.resolve(campaign)
        recipients = []
        for user in users:
            for channel in campaign.channels:
                recipients.append(
                    NotificationRecipients(
                        notification=campaign,
                        user=user,
                        channel=channel,
                        status="PENDING"
                    )
                )
        NotificationRecipients.objects.bulk_create(
            recipients,
            batch_size=1000
        )
        campaign.total_recipients = len(recipients)
        campaign.status = "QUEUED"
        campaign.save(
            update_fields=[
                "total_recipients",
                "status"
            ]
        )
        return True