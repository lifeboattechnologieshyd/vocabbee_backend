from django.urls import path

from .support import AdminSupportTicketsAPIView, AdminSupportTicketDetailAPIView, AdminReplySupportTicketAPIView, \
    AdminUpdateSupportTicketStatusAPIView
from .views import SendOtp, VerifyOTP, GradesList, WordsCrud, UploadWords, MakeAdmin, WordsAudio

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("make-admin", MakeAdmin.as_view()),
    path("grades", GradesList.as_view()),
    path("grades/update", GradesList.as_view()), # PUT
    path("grades/delete", GradesList.as_view()),
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

]