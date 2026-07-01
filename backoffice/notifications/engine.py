from django.utils import timezone

from backoffice.notifications.PushSender import PushSender


class NotificationEngine:
    SENDERS = {
        "PUSH": PushSender,
        # "EMAIL": EmailSender,
        # "SMS": SmsSender,
        # "WHATSAPP": WhatsAppSender,
        # "IN_APP": InAppSender
    }
    @classmethod
    def process_recipient(cls, recipient):
        sender = cls.SENDERS.get(recipient.channel)
        if not sender:
            recipient.status = "FAILED"
            recipient.failure_reason = "Unsupported notification channel."
            recipient.save(
                update_fields=[
                    "status",
                    "failure_reason"
                ]
            )
            return False
        result = sender.send(recipient=recipient)
        recipient.provider_response = result.get("provider_response", "No Response")
        recipient.status = (
            "SENT"
            if result["success"]
            else "FAILED"
        )
        if recipient.status == 'FAILED':
            recipient.failure_reason = result.get("provider_response", "No Reason")
        else:
            recipient.sent_at = timezone.now()

        recipient.save(
            update_fields=[
                "status",
                "sent_at",
                "failure_reason",
                "provider_response"
            ]
        )
        return True



