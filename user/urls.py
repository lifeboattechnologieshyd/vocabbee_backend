from django.urls import path

from .practice import StartPractice, SubmitPracticeAnswer, SkipPracticeQuestion, EndPractice, PracticeStats, \
    PracticeHistoryAPIView
from .views import SendOtp, VerifyOTP, Profile, GradesList, AddKid, ApplyReferral, FileUploadView

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("profile", Profile.as_view()),
    path("grades", GradesList.as_view()),
    path("kids", AddKid.as_view()),
    path("apply/referral", ApplyReferral.as_view()),

    path("practice/start", StartPractice.as_view()),
    path("practice/submit-answer", SubmitPracticeAnswer.as_view()),
    path("practice/skip-answer", SkipPracticeQuestion.as_view()),
    path("practice/end", EndPractice.as_view()),

    path("practice/stats", PracticeStats.as_view()),
    path("practice/attempts", PracticeHistoryAPIView.as_view()),

    path("file/upload",FileUploadView.as_view()),


]