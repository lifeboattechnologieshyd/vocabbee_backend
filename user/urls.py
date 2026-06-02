from django.urls import path
from .views import SendOtp

urlpatterns = [
    path("user/send-otp", SendOtp.as_view()),
    path("user/verify-otp", SendOtp.as_view()),

]