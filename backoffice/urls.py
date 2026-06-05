from django.urls import path
from .views import SendOtp, VerifyOTP, GradesList

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("grades", GradesList.as_view()),
    path("grades/update", GradesList.as_view()), # PUT
    path("grades/delete", GradesList.as_view()), # DELETE

]