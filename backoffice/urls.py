from django.urls import path
from .views import SendOtp, VerifyOTP

urlpatterns = [
    path("backoffice/send-otp", SendOtp.as_view()),
    path("backoffice/verify-otp", VerifyOTP.as_view()),

]