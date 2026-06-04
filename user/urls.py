from django.urls import path
from .views import SendOtp, VerifyOTP, Profile, GradesList

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("profile", Profile.as_view()),
    path("grades", GradesList.as_view()),
]