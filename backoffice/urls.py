from django.urls import path

from .compete import TournamentCreateAPIView, TournamentDetailsAPIView, TournamentAssignGradesAPIView
from .notifications.campaign_service import CreateNotificationCampaignAPIView
from .support import AdminSupportTicketsAPIView, AdminSupportTicketDetailAPIView, AdminReplySupportTicketAPIView, \
    AdminUpdateSupportTicketStatusAPIView
from .views import SendOtp, VerifyOTP, GradesList, WordsCrud, UploadWords, MakeAdmin, WordsAudio, DashboardAPIView, \
    SubjectCrud, SubjectDeleteAPIView

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("make-admin", MakeAdmin.as_view()),
    path("grades", GradesList.as_view()),
    path("grades/update", GradesList.as_view()), # PUT
    path("grades/delete", GradesList.as_view()),


    path("subject", SubjectCrud.as_view()),
    path("subject/<uuid:subject_id>", SubjectDeleteAPIView.as_view()),


    # DELETE
    path("words", WordsCrud.as_view()), #crud
    path("words/audio", WordsAudio.as_view()), #get audio from sf
    path("words/bulk", UploadWords.as_view()), #excel upload

    ##############################################
    ## Support Module Api's
    ##############################################
    path("support/tickets", AdminSupportTicketsAPIView.as_view()),
    path("support/ticket-details", AdminSupportTicketDetailAPIView.as_view()),
    path("support/reply", AdminReplySupportTicketAPIView.as_view()),
    path("support/ticket/update", AdminUpdateSupportTicketStatusAPIView.as_view()),

    path("dashboard", DashboardAPIView.as_view()),

    # create notification service
    path("create-campaign", CreateNotificationCampaignAPIView.as_view()),

    path("tournament", TournamentCreateAPIView.as_view()),
    path("tournament-details/<uuid:tournament_id>", TournamentDetailsAPIView.as_view()),
    path("tournament-assign-grades/<uuid:tournament_id>", TournamentAssignGradesAPIView.as_view()),

]