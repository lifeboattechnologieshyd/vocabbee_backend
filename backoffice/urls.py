from django.urls import path
from .views import SendOtp, VerifyOTP

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),

]