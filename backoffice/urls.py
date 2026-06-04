from django.urls import path
from .views import SendOtp, VerifyOTP

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("grades", VerifyOTP.as_view()),
    path("grades/update", VerifyOTP.as_view()), # PUT
    path("grades/delete", VerifyOTP.as_view()), # DELETE

]