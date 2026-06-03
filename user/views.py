import random
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from db.models.user import OTPs, UserMaster
from shared.clients.sms import send_otp_sms
from shared.utils import CustomResponse

class SendOtp(APIView):

    def post(self, request):
        mobile = request.data.get("mobile")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile number is required"
            )
        last_otp = OTPs.objects.filter(
            mobile_number=mobile,
            created_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if last_otp:
            return CustomResponse().errorResponse(
                data={},
                description="Please wait before requesting another OTP"
            )
        otp = str(random.randint(1000, 9999))
        otp = "1234"
        OTPs.objects.filter(
            mobile_number=mobile,
            is_active=True
        ).update(
            is_active=False
        )
        OTPs.objects.create(
            mobile_number=mobile,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5),
            is_active=True
        )
        send_otp_sms(mobile, otp)
        print(f"OTP for {mobile} : {otp}")
        return CustomResponse().successResponse(
            data={},
            description="OTP sent successfully"
        )

class VerifyOTP(APIView):

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile number is required"
            )
        if not otp:
            return CustomResponse().errorResponse(
                data={},
                description="OTP is required"
            )
        otp_record = OTPs.objects.filter(
            mobile_number=mobile,
            otp=otp,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        if not otp_record:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid or expired OTP"
            )
        otp_record.is_active = False
        otp_record.save()
        user = UserMaster.objects.filter(
            mobile=mobile
        ).first()
        if not user:
            user = UserMaster.objects.create_user(
                mobile=mobile,
                is_mobile_verified=True,
                user_role = ["parent"]
            )

        else:
            if not user.is_mobile_verified:
                user.is_mobile_verified = True
                user.save()

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        refresh = RefreshToken.for_user(user)
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "is_profile_completed": bool(user.full_name)
            },
            description="Login successful"
        )


class Profile(APIView):

    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "is_profile_completed": user.is_profile_completed
            },
            description="Profile fetched successfully"
        )

    def put(self, request):

        user = request.user
        full_name = request.data.get("full_name")
        profile_image = request.data.get("profile_image")

        if not full_name:
            return CustomResponse().errorResponse(
                data={},
                description="Full name is required"
            )

        user.full_name = full_name.strip()

        if profile_image is not None:
            user.profile_image = profile_image

        user.save()

        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "is_profile_completed": True
            },
            description="Profile updated successfully"
        )