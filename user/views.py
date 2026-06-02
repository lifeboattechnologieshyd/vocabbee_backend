import random
from datetime import timedelta

from django.utils import timezone
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
        # https://full2ads.com/smsapi/index?key=26911C63F0A654&campaign=0&routeid=1&type=text&contacts={mobile}&senderid=VOCABE&tlv=%7B%22DLT_ENTITY_ID%22%3A%221001548232379518414%22%2C%22DLT_TEMPLATE_ID%22%3A%221107178030754522073%22%7D&type=text&msg=Use%20OTP%20{otp}%20to%20login%20to%20VOCABBEE.%20OTP%20is%20valid%20for%2010%20minutes.%20Do%20not%20share%20th%20is%20OTP%20with%20anyone.
        # deactivate previous active OTPs
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
                is_mobile_verified=True
            )

        else:
            if not user.is_mobile_verified:
                user.is_mobile_verified = True
                user.save()

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