from rest_framework.views import APIView

from backoffice.notifications.campaign_dispatcher import CampaignDispatcher
from backoffice.notifications.recipient_builder import CampaignQueueBuilder
from db.models import NotificationCampaign
from shared.utils import CustomResponse


class CampaignService:

    @staticmethod
    def create_campaign(
        *,
        title,
        body,
        audience,
        channels,
        created_by,
        payload=None,
        image=None,
        grade_ids=None,
        user_ids=None,
        kid_ids=None,
        scheduled_at=None
    ):

        campaign = NotificationCampaign.objects.create(
            title=title,
            body=body,
            audience=audience,
            channels=channels,
            payload=payload or {},
            image=image,
            grade_ids=grade_ids or [],
            user_ids=user_ids or [],
            kid_ids=kid_ids or [],
            scheduled_at=scheduled_at,
            created_by=created_by,
            status="DRAFT"
        )
        CampaignQueueBuilder.build(campaign)
        campaign = CampaignDispatcher.process(campaign)
        return campaign


class CreateNotificationCampaignAPIView(APIView):

    def post(self, request):
        try:
            title = request.data.get("title")
            body = request.data.get("body")
            audience = request.data.get("audience")
            channels = request.data.get("channels")
            if not title:
                return CustomResponse().errorResponse(data={},
                    description="Title is required."
                )
            campaign = CampaignService.create_campaign(
                title=title,
                body=body,
                audience=audience,
                channels=channels,
                payload=request.data.get("payload"),
                image=request.data.get("image"),
                grade_ids=request.data.get("grade_ids"),
                user_ids=request.data.get("user_ids"),
                kid_ids=request.data.get("kid_ids"),
                scheduled_at=request.data.get("scheduled_at"),
                created_by=None
            )
            return CustomResponse().successResponse(
                description="Notification campaign created successfully.",
                data={}
            )

        except Exception as error:
            return CustomResponse().errorResponse(data={}, description=error)