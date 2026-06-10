import os
import random
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlparse

import requests
from boto3 import s3
from boto3.s3.inject import download_file
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models.user import OTPs, UserMaster, Grades, Words, WordAudios
from shared.clients.s3 import save_to_s3
from shared.clients.sms import send_otp_sms
from shared.helper import import_word_from_schoolfirst
from shared.utils import CustomResponse

class SendOtp(APIView):

    def post(self, request):
        mobile = request.data.get("mobile")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile number is required"
            )
        user = UserMaster.objects.filter(
            mobile=mobile
        ).first()
        if not user:
            return CustomResponse().errorResponse(
                data={},
                description="Any account with this number does not exist"
            )
        if not user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="You Don't have access to login"
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
class MakeAdmin(APIView):
    def post(self, request):
        mobile = request.data.get("mobile")
        user = UserMaster.objects.filter(mobile=mobile).first()
        if not user:
            return CustomResponse().errorResponse(
                data={},
                description="No user found with mobile"
            )
        if not user.is_admin:
            user.user_role = ['admin', 'parent']
            user.save()
            return CustomResponse().successResponse(data={},description="User Role changed")
        else:
            return CustomResponse().errorResponse(data={},description="You are already an admin")

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
        if not user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="You don't have access to use this"
            )
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

class GradesList(APIView):

    def get(self, request):

        grades = Grades.objects.filter(
            is_active=True
        ).order_by(
            "sort_order"
        )

        response = []

        for grade in grades:

            response.append({
                "grade_id": str(grade.id),
                "name": grade.name
            })

        return CustomResponse().successResponse(
            data=response,
            description="Grades fetched successfully"
        )

    def post(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        name = request.data.get("name")
        sort_order = request.data.get("sort_order", 1)
        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Grade name is required"
            )
        grade = Grades.objects.create(
            name=name,
            sort_order=sort_order
        )
        return CustomResponse().successResponse(
            data={
                "grade_id": str(grade.id)
            },
            description="Grade created successfully"
        )
    def put(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )

        grade_id = request.data.get("grade_id")

        grade = Grades.objects.filter(
            id=grade_id,
            is_active=True
        ).first()
        if not grade:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid grade"
            )
        name = request.data.get("name")
        sort_order = request.data.get("sort_order")
        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Grade name is required"
            )
        grade.name = name
        if sort_order is not None:
            grade.sort_order = sort_order
        grade.save()
        return CustomResponse().successResponse(
            data={
                "grade_id": str(grade.id)
            },
            description="Grade updated successfully"
        )

    def delete(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        grade_id = request.data.get("grade_id")
        grade = Grades.objects.filter(
            id=grade_id,
            is_active=True
        ).first()
        if not grade:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid grade"
            )
        grade.is_active = False
        grade.save()
        return CustomResponse().successResponse(
            data={},
            description="Grade deleted successfully"
        )
import pandas as pd

class WordsAudio(APIView):

    def download_file_from_s3(self, url, word):
        audio_response = requests.get(url)
        audio_response.raise_for_status()
        audio_file = BytesIO(audio_response.content)
        filename = os.path.basename(urlparse(url).path)
        audio_file.name = filename
        return save_to_s3(
            path="words",
            file_obj=audio_file
        )

    def post(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        word_id = request.data.get("word_id")
        word = Words.objects.filter(id=word_id, status='PENDING').first()
        if not word:
            return CustomResponse().errorResponse(
                data={},
                description="No Word found with provided ID or already generated"
            )
        data = import_word_from_schoolfirst(word.word)
        if not data:
            return CustomResponse().errorResponse(
                data={},
                description="No Word found in School First"
            )

        pronunciation_audio_url = data["pronunciation_audio"]
        meaning_audio_url = data["meaning_audio"]
        part_of_speech_audio_url = data["part_of_speech_audio"]
        origin_audio_url = data["origin_audio"]
        usage_audio_url = data["usage_audio"]
        p_a_u = self.download_file_from_s3(pronunciation_audio_url, word)
        m_a_u = self.download_file_from_s3(meaning_audio_url, word)
        ps_a_u = self.download_file_from_s3(part_of_speech_audio_url, word)
        o_a_u = self.download_file_from_s3(origin_audio_url, word)
        u_a_u = self.download_file_from_s3(usage_audio_url, word)

        word.usage = data["usage"]
        word.meaning = data["meaning"]
        word.part_of_speech = data["part_of_speech"]
        word.origin = data["origin"]


        WordAudios.objects.update_or_create(
            word=word,
            defaults={
                "pronunciation_audio_url": p_a_u,
                "meaning_audio_url": m_a_u,
                "part_of_speech_audio_url": ps_a_u,
                "origin_audio_url":o_a_u,
                "usage_audio_url":u_a_u,
            }
        )
        word.status = "GENERATED"
        word.save()
        return CustomResponse().successResponse(
            data={},
            description="Audio files generated."
        )


class WordsCrud(APIView):

    def post(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        grade_id = request.data.get("grade_id")
        word = request.data.get("word")
        if not grade_id:
            return CustomResponse().errorResponse(
                data={},
                description="Grade is required"
            )
        if not word:
            return CustomResponse().errorResponse(
                data={},
                description="Word is required"
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
        if Words.objects.filter(
                word__iexact=word.strip()
        ).exists():
            return CustomResponse().errorResponse(
                data={},
                description="Word already exists"
            )
        word_obj = Words.objects.create(
            grade=grade,
            word=word.strip(),
            difficulty=request.data.get(
                "difficulty",
                1
            ),
            meaning=request.data.get(
                "meaning"
            ),
            part_of_speech=request.data.get(
                "part_of_speech"
            ),
            origin=request.data.get(
                "origin"
            ),
            usage=request.data.get(
                "usage"
            )
        )
        return CustomResponse().successResponse(
            data={
                "word_id": str(word_obj.id)
            },
            description="Word created successfully"
        )

    def get(self, request):

        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))
        search = request.GET.get("search")
        grade_id = request.GET.get("grade_id")
        difficulty = request.GET.get("difficulty")

        words = Words.objects.filter(
            is_active=True
        ).select_related(
            "grade"
        )

        if grade_id:
            words = words.filter(
                grade_id=grade_id
            )

        if difficulty:
            words = words.filter(
                difficulty=difficulty
            )

        if search:
            words = words.filter(
                Q(word__icontains=search)
                |
                Q(meaning__icontains=search)
            )
        total_count = words.count()
        start = (page - 1) * page_size
        end = start + page_size
        words = words.order_by(
            "word"
        )[start:end]
        response = []
        for word in words:
            response.append({
                "word_id": str(word.id),
                "word": word.word,
                "difficulty": word.difficulty,
                "meaning": word.meaning,
                "part_of_speech": word.part_of_speech,
                "origin": word.origin,
                "usage": word.usage,
                "grade": {
                    "id": str(word.grade.id),
                    "name": word.grade.name
                }
            })

        return CustomResponse().successResponse(
            data=response,
            total=total_count,
            description="Words fetched successfully"
        )

    def put(self, request):

        word_id = request.data.get(
            "word_id"
        )

        word_obj = Words.objects.filter(
            id=word_id,
            is_active=True
        ).first()

        if not word_obj:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid word"
            )

        grade_id = request.data.get(
            "grade_id"
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

        new_word = request.data.get(
            "word"
        )

        duplicate = Words.objects.filter(
            word__iexact=new_word
        ).exclude(
            id=word_obj.id
        ).exists()

        if duplicate:
            return CustomResponse().errorResponse(
                data={},
                description="Word already exists"
            )

        word_obj.word = new_word.strip()
        word_obj.grade = grade

        word_obj.difficulty = request.data.get(
            "difficulty",
            word_obj.difficulty
        )

        word_obj.meaning = request.data.get(
            "meaning",
            word_obj.meaning
        )

        word_obj.part_of_speech = request.data.get(
            "part_of_speech",
            word_obj.part_of_speech
        )

        word_obj.origin = request.data.get(
            "origin",
            word_obj.origin
        )

        word_obj.usage = request.data.get(
            "usage",
            word_obj.usage
        )
        word_obj.save()
        return CustomResponse().successResponse(
            data={},
            description="Word updated successfully"
        )
    def delete(self, request):
        word_id = request.data.get(
            "word_id"
        )
        word_obj = Words.objects.filter(
            id=word_id,
            is_active=True
        ).first()
        if not word_obj:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid word"
            )
        word_obj.is_active = False
        word_obj.save()
        return CustomResponse().successResponse(
            data={},
            description="Word deleted successfully"
        )

class UploadWords(APIView):

    def post(self, request):

        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )

        file = request.FILES.get("file")

        if not file:
            return CustomResponse().errorResponse(
                data={},
                description="File is required"
            )

        try:

            df = pd.read_excel(file)
            required_columns = [
                "Grade",
                "Word",
                "Difficulty"
            ]
            missing_columns = [
                column
                for column in required_columns
                if column not in df.columns
            ]

            if missing_columns:

                return CustomResponse().errorResponse(
                    data={},
                    description=f"Missing columns: {', '.join(missing_columns)}"
                )

            grades_map = {
                grade.name.strip().lower(): grade
                for grade in Grades.objects.filter(
                    is_active=True
                )
            }

            existing_words = set(
                Words.objects.filter(
                    is_active=True
                ).values_list(
                    "word",
                    flat=True
                )
            )

            words_to_create = []

            skipped_count = 0

            for _, row in df.iterrows():

                grade_name = str(
                    row["Grade"]
                ).strip()

                word = str(
                    row["Word"]
                ).strip()

                if not word:
                    continue

                grade = grades_map.get(
                    grade_name.lower()
                )

                if not grade:
                    skipped_count += 1
                    continue

                if word in existing_words:
                    skipped_count += 1
                    continue

                words_to_create.append(
                    Words(
                        grade=grade,
                        word=word,
                        difficulty=row.get(
                            "Difficulty",
                            1
                        ),
                        meaning=row.get(
                            "Meaning"
                        ),
                        part_of_speech=row.get(
                            "Part Of Speech"
                        ),
                        origin=row.get(
                            "Origin"
                        ),
                        usage=row.get(
                            "Usage"
                        )
                    )
                )

                existing_words.add(word)

            Words.objects.bulk_create(
                words_to_create,
                batch_size=1000
            )

            return CustomResponse().successResponse(
                data={
                    "created_count": len(words_to_create),
                    "skipped_count": skipped_count
                },
                description="Words uploaded successfully"
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )


