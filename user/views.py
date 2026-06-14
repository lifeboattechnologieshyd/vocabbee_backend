import random
from datetime import timedelta

from django.core.files.storage import default_storage
from django.conf import settings
from rest_framework.parsers import FormParser, MultiPartParser

from rest_framework import status

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models.user import OTPs, UserMaster, Grades, Kids, PracticeAttempts, KidWordProgress, Words, \
    PracticeAttemptAnswers, Referrals, CoinTransactions
from shared.clients.s3 import add_unique_suffix_to_filename, sanitize_filename
from django.core.files.base import ContentFile
from shared.clients.sms import send_otp_sms
from shared.helper import get_practice_words, getReferralCode
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
        if mobile == '9014083090':
            otp = "1234"
        # otp = "1234"
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
                referral_code=getReferralCode(),
                user_role = ["parent"]
            )
        else:
            if not user.is_mobile_verified:
                user.is_mobile_verified = True
                user.save()
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        refresh = RefreshToken.for_user(user)
        can_apply_referral = not Referrals.objects.filter(
            referred_user=user
        ).exists()
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "referral_code": user.referral_code,
                "coins": user.coins,
                "is_profile_completed": bool(user.full_name),
                "can_apply_referral": can_apply_referral,
                "kids": user.kids.count()
            },
            description="Login successful"
        )


class Profile(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        can_apply_referral = not Referrals.objects.filter(
            referred_user=request.user
        ).exists()
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "referral_code": user.referral_code,
                "coins": user.coins,
                "dob": user.dob,
                "email": user.email,
                "gender": user.gender,
                "kids": user.kids.count(),
                "can_apply_referral": can_apply_referral,
                "is_profile_completed": user.is_profile_completed
            },
            description="Profile fetched successfully"
        )

    def put(self, request):

        user = request.user
        full_name = request.data.get("full_name")
        profile_image = request.data.get("profile_image")
        gender = request.data.get("gender")
        dob = request.data.get("dob")
        email = request.data.get("email")

        if not full_name:
            return CustomResponse().errorResponse(
                data={},
                description="Full name is required"
            )

        user.full_name = full_name.strip()

        if profile_image is not None:
            user.profile_image = profile_image
        if gender is not None:
            user.gender = gender
        if dob is not None:
            user.dob = dob
        if email is not None:
            user.email = email

        user.save()

        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "gender": user.gender,
                "dob": user.dob,
                "email": user.email,
                "is_profile_completed": True
            },
            description="Profile updated successfully"
        )

class GradesList(APIView):
    def get(self, request):
        grades = Grades.objects.filter(
                is_active=True
            ).order_by(
                "sort_order"
            )
        data = []
        for grade in grades:
            data.append({
                "id": str(grade.id),
                "name": grade.name
            })
        return CustomResponse().successResponse(
            data=data,
            description="Grades fetched successfully"
        )


class AddKid(APIView):

    def post(self, request):

        name = request.data.get("name")
        grade_id = request.data.get("grade_id")
        profile_image = request.data.get("profile_image")

        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Kid name is required"
            )

        if not grade_id:
            return CustomResponse().errorResponse(
                data={},
                description="Grade is required"
            )
        grade = Grades.objects.filter(
            id=grade_id,
            is_active=True
        ).first()
        if not grade:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid grade"
            )
        kid = Kids.objects.create(
            parent=request.user,
            grade=grade,
            name=name,
            profile_image=profile_image
        )
        return CustomResponse().successResponse(
            data={
                "kid_id": str(kid.id)
            },
            description="Kid added successfully"
        )

    def get(self, request):
        kids = request.user.kids.filter(
            is_active=True
        ).select_related(
            "grade"
        )

        response = []
        for kid in kids:
            response.append({
                "kid_id": str(kid.id),
                "name": kid.name,
                "profile_image": kid.profile_image,
                "grade": {
                    "id": str(kid.grade.id),
                    "name": kid.grade.name
                }
            })
        return CustomResponse().successResponse(
            data=response,
            description="Kids fetched successfully"
        )
    def put(self, request):

        kid_id = request.data.get("kid_id")

        if not kid_id:
            return CustomResponse().errorResponse(
                data={},
                description="Kid ID is required"
            )

        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid kid"
            )

        name = request.data.get("name")
        grade_id = request.data.get("grade_id")
        profile_image = request.data.get("profile_image")

        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Kid name is required"
            )

        grade = Grades.objects.filter(
            id=grade_id,
            is_active=True
        ).first()

        if not grade:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid grade"
            )

        kid.name = name.strip()
        kid.grade = grade

        if profile_image is not None:
            kid.profile_image = profile_image

        kid.save()

        return CustomResponse().successResponse(
            data={},
            description="Kid updated successfully"
        )

    def delete(self, request):

        kid_id = request.data.get("kid_id")

        if not kid_id:
            return CustomResponse().errorResponse(
                data={},
                description="Kid ID is required"
            )

        kid = request.user.kids.filter(
            id=kid_id,
            is_active=True
        ).first()

        if not kid:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid kid"
            )

        kid.is_active = False
        kid.save()
        return CustomResponse().successResponse(
            data={},
            description="Kid deleted successfully"
        )


class ApplyReferral(APIView):

    REFERRER_COINS = 50
    REFERRED_USER_COINS = 25

    @transaction.atomic
    def post(self, request):

        referral_code = request.data.get(
            "referral_code",
            ""
        ).strip().upper()

        if not referral_code:

            return CustomResponse().errorResponse(
                data={},
                description="Referral code is required"
            )

        if Referrals.objects.filter(
            referred_user=request.user
        ).exists():

            return CustomResponse().errorResponse(
                data={},
                description="Referral code already applied"
            )

        referrer = UserMaster.objects.filter(
            referral_code=referral_code,
            is_active=True
        ).first()

        if not referrer:

            return CustomResponse().errorResponse(
                data={},
                description="Invalid referral code"
            )

        if referrer.id == request.user.id:

            return CustomResponse().errorResponse(
                data={},
                description="You cannot use your own referral code"
            )

        referral = Referrals.objects.create(
            referrer=referrer,
            referred_user=request.user,
            referral_code=referral_code,
            reward_coins=self.REFERRER_COINS
        )

        referrer.coins += self.REFERRER_COINS

        request.user.coins += self.REFERRED_USER_COINS

        referrer.save(
            update_fields=[
                "coins",
                "updated_at"
            ]
        )

        request.user.save(
            update_fields=[
                "coins",
                "updated_at"
            ]
        )

        CoinTransactions.objects.create(
            user=referrer,
            coins=self.REFERRER_COINS,
            transaction_type="REFERRAL_BONUS",
            reference_id=referral.id,
            remarks=f"Referral reward for {request.user.mobile}",
            balance_after_transaction=referrer.coins
        )

        CoinTransactions.objects.create(
            user=request.user,
            coins=self.REFERRED_USER_COINS,
            transaction_type="REFERRAL_JOIN_BONUS",
            reference_id=referral.id,
            remarks=f"Joined using referral code {referral_code}",
            balance_after_transaction=request.user.coins
        )

        return CustomResponse().successResponse(
            data={
                "coins": request.user.coins
            },
            description="Referral applied successfully"
        )

class FileUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist("files")
        path = request.data.get("path", "temp")

        if not files:
            return CustomResponse().successResponse(
                {"error": "No file was provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_files = []

        try:
            for file_obj in files:
                # Save each file to the default storage
                sanitized_filename = add_unique_suffix_to_filename(sanitize_filename(file_obj.name))

                file_path = default_storage.save(f"{path}/{sanitized_filename}", ContentFile(file_obj.read()))
                file_url = settings.MEDIA_URL + file_path
                uploaded_files.append(
                    {"original_filename": file_obj.name, "file_url": file_url, "file_path": file_path}
                )

            return CustomResponse().successResponse(uploaded_files, status=status.HTTP_201_CREATED)

        except Exception as e:
            return CustomResponse().errorResponse(
                {"error": str(e)}, description="File upload failed", status=status.HTTP_400_BAD_REQUEST
            )






