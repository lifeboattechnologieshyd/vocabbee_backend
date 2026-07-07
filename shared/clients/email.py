from django.core.mail import send_mail
from django.conf import settings


def send_email_otp(email, otp):
    send_mail(
        subject="Your Vocabbee OTP",
        message=f"""
Hello,

Your OTP is {otp}

It is valid for 5 minutes.

Regards,
Vocabbee Team
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False
    )