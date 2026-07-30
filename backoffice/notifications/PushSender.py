from config.firebase import send_visible_push_notification


class PushSender:
    @classmethod
    def send(cls, recipient):
        campaign = recipient.notification
        return send_visible_push_notification(
            user=recipient.user,
            title=campaign.title,
            body=campaign.body,
            notification_type=campaign.payload.get(
                "type",
                "GENERAL"
            ),
            payload=campaign.payload
        )


