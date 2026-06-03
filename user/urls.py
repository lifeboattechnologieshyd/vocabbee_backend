from django.urls import path
from .views import SendOtp,VerifyOTP

urlpatterns = [
    path("user/send-otp", SendOtp.as_view()),
    path("user/verify-otp", VerifyOTP.as_view()),

]