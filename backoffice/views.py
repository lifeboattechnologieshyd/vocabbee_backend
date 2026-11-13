import os
import random
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlparse

import requests
from boto3 import s3
from boto3.s3.inject import download_file
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models.user import OTPs, UserMaster, Grades, Words, WordAudios, PracticeAttempts, Subjects
from shared.clients.s3 import save_to_s3
from shared.clients.sms import send_sms_to_mobile
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
            identifier=mobile,
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
            identifier=mobile,
            is_active=True
        ).update(
            is_active=False
        )
        OTPs.objects.create(
            identifier=mobile,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5),
            is_active=True
        )
        send_sms_to_mobile(otp, mobile, 12596)
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
            identifier=mobile,
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


def download_file_from_s3(url, word):
    audio_response = requests.get(url)
    audio_response.raise_for_status()
    audio_file = BytesIO(audio_response.content)
    filename = os.path.basename(urlparse(url).path)
    audio_file.name = filename
    return save_to_s3(
        path="words",
        file_obj=audio_file
    )

def getWordAudio(word: Words):
    data = import_word_from_schoolfirst(word.word)
    if not data:
        # todo- we have to use google ai or tts to generate audio
        return False, "No Word found in SchoolFirst"
    pronunciation_audio_url = data["pronunciation_audio"]
    meaning_audio_url = data["meaning_audio"]
    part_of_speech_audio_url = data["part_of_speech_audio"]
    origin_audio_url = data["origin_audio"]
    usage_audio_url = data["usage_audio"]
    p_a_u = download_file_from_s3(pronunciation_audio_url, word)
    m_a_u = download_file_from_s3(meaning_audio_url, word)
    ps_a_u = download_file_from_s3(part_of_speech_audio_url, word)
    o_a_u = download_file_from_s3(origin_audio_url, word)
    u_a_u = download_file_from_s3(usage_audio_url, word)

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
            "origin_audio_url": o_a_u,
            "usage_audio_url": u_a_u,
        }
    )
    word.voice_status = "GENERATED"
    word.save()
    return True, "Audio files generated."


class WordsAudio(APIView):

    def post(self, request):
        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )
        word_id = request.data.get("word_id")
        word = Words.objects.filter(id=word_id, voice_status='PENDING').first()
        if not word:
            return CustomResponse().errorResponse(
                data={},
                description="No Word found with provided ID or already generated"
            )
        resp = getWordAudio(word)
        if resp[0]:
            return CustomResponse().successResponse(
                data={},
                description="Audio files generated."
            )
        else:
            return CustomResponse().errorResponse(
                data={},
                description=resp[1]
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

        if not word or not word.strip():
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

        word = word.strip()

        if Words.objects.filter(
            grade=grade,
            word__iexact=word
        ).exists():
            return CustomResponse().errorResponse(
                data={},
                description="Word already exists for this grade"
            )

        word_obj = Words.objects.create(
            grade=grade,
            word=word,
            subject=request.data.get("subject", "English"),
            concept=request.data.get("concept"),
            hint=request.data.get("hint"),
            meaning=request.data.get("meaning"),
            difficulty=request.data.get("difficulty", 1),
            part_of_speech=request.data.get("part_of_speech"),
            origin=request.data.get("origin"),
            usage=request.data.get("usage"),

            # New fields
            root_word=request.data.get("root_word"),
            phonetic_script=request.data.get("phonetic_script"),
            syllabified_stressed_transcript=request.data.get(
                "syllabified_stressed_transcript"
            ),
            origin_word=request.data.get("origin_word"),
            origin_word_meaning=request.data.get("origin_word_meaning"),
            antonym=request.data.get("antonym"),
            synonym=request.data.get("synonym"),
            points=request.data.get("points", 0),
            word_status=request.data.get("word_status"),
            domain=request.data.get("domain"),
        )

        resp = getWordAudio(word_obj)

        return CustomResponse().successResponse(
            data={
                "word_id": str(word_obj.id),
                "audio_generated": resp[0],
                "audio_description": resp[1],
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
            is_active=True,
            voice_status="GENERATED"
        ).select_related(
            "grade",
            "audio"
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
            )

        total_count = words.count()

        start = (page - 1) * page_size
        end = start + page_size

        words = words.order_by(
            "is_valid",
            "word"
        )[start:end]

        response = []

        for word in words:

            word_details = {
                "word_id": str(word.id),
                "word": word.word,
                "subject": word.subject,
                "concept": word.concept,
                "hint": word.hint,
                "difficulty": word.difficulty,
                "meaning": word.meaning,
                "part_of_speech": word.part_of_speech,
                "origin": word.origin,
                "usage": word.usage,

                # New fields
                "root_word": word.root_word,
                "phonetic_script": word.phonetic_script,
                "syllabified_stressed_transcript": (
                    word.syllabified_stressed_transcript
                ),
                "origin_word": word.origin_word,
                "origin_word_meaning": word.origin_word_meaning,
                "antonym": word.antonym,
                "synonym": word.synonym,
                "points": word.points,
                "word_status": word.word_status,
                "domain": word.domain,

                # Existing fields
                "voice_status": word.voice_status,
                "is_valid": word.is_valid,
                "validation_reason": word.validation_reason,
                "validation_source": word.validation_source,
                "validated_at": word.validated_at,

                "grade": {
                    "id": str(word.grade.id),
                    "name": word.grade.name
                }
            }

            if hasattr(word, "audio"):
                word_details["pronunciation_audio_url"] = (
                    word.audio.pronunciation_audio_url
                )
                word_details["meaning_audio_url"] = (
                    word.audio.meaning_audio_url
                )
                word_details["part_of_speech_audio_url"] = (
                    word.audio.part_of_speech_audio_url
                )
                word_details["origin_audio_url"] = (
                    word.audio.origin_audio_url
                )
                word_details["usage_audio_url"] = (
                    word.audio.usage_audio_url
                )
                word_details["syllabified_stressed_transcript_audio_url"] = (
                    word.audio.syllabified_stressed_transcript_audio_url
                )
                word_details["phonetic_script_audio_url"] = (
                    word.audio.phonetic_script_audio_url
                )

            response.append(word_details)

        return CustomResponse().successResponse(
            data=response,
            total=total_count,
            description="Words fetched successfully"
        )

    def put(self, request):

        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )

        word_id = request.data.get("word_id")

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
            "grade_id",
            word_obj.grade_id
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
            "word",
            word_obj.word
        )

        if not new_word or not new_word.strip():
            return CustomResponse().errorResponse(
                data={},
                description="Word is required"
            )

        new_word = new_word.strip()

        duplicate = Words.objects.filter(
            grade=grade,
            word__iexact=new_word,
            is_active=True
        ).exclude(
            id=word_obj.id
        ).exists()

        if duplicate:
            return CustomResponse().errorResponse(
                data={},
                description="Word already exists for this grade"
            )

        word_obj.word = new_word
        word_obj.grade = grade

        # Existing fields
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

        word_obj.subject = request.data.get(
            "subject",
            word_obj.subject
        )

        word_obj.origin = request.data.get(
            "origin",
            word_obj.origin
        )

        word_obj.usage = request.data.get(
            "usage",
            word_obj.usage
        )

        word_obj.hint = request.data.get(
            "hint",
            word_obj.hint
        )

        word_obj.concept = request.data.get(
            "concept",
            word_obj.concept
        )

        # New fields
        word_obj.root_word = request.data.get(
            "root_word",
            word_obj.root_word
        )

        word_obj.phonetic_script = request.data.get(
            "phonetic_script",
            word_obj.phonetic_script
        )

        word_obj.syllabified_stressed_transcript = request.data.get(
            "syllabified_stressed_transcript",
            word_obj.syllabified_stressed_transcript
        )

        word_obj.origin_word = request.data.get(
            "origin_word",
            word_obj.origin_word
        )

        word_obj.origin_word_meaning = request.data.get(
            "origin_word_meaning",
            word_obj.origin_word_meaning
        )

        word_obj.antonym = request.data.get(
            "antonym",
            word_obj.antonym
        )

        word_obj.synonym = request.data.get(
            "synonym",
            word_obj.synonym
        )

        word_obj.points = request.data.get(
            "points",
            word_obj.points
        )

        word_obj.word_status = request.data.get(
            "word_status",
            word_obj.word_status
        )

        word_obj.domain = request.data.get(
            "domain",
            word_obj.domain
        )

        # Manual validation
        if "is_valid" in request.data:

            word_obj.is_valid = request.data.get("is_valid")

            word_obj.validation_reason = request.data.get(
                "validation_reason",
                word_obj.validation_reason
            )

            word_obj.validation_source = Words.ValidationSource.MANUAL
            word_obj.validated_at = timezone.now()
            word_obj.validated_by = request.user

        word_obj.updated_by = str(request.user)

        word_obj.save()

        return CustomResponse().successResponse(
            data={
                "word_id": str(word_obj.id)
            },
            description="Word updated successfully"
        )

    def delete(self, request):

        if not request.user.is_admin:
            return CustomResponse().errorResponse(
                data={},
                description="Unauthorized"
            )

        word_id = request.data.get("word_id")

        word_obj = Words.objects.filter(
            id=word_id,
            is_active=True,
            is_valid=False
        ).first()

        if not word_obj:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid word"
            )

        word_obj.is_active = False
        word_obj.updated_by = str(request.user)
        word_obj.save()

        return CustomResponse().successResponse(
            data={},
            description="Word deleted successfully"
        )


# class UploadWords(APIView):
#
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser, FormParser]
#
#     def post(self, request):
#
#         # if not request.user.is_admin:
#         #     return CustomResponse().errorResponse(
#         #         data={},
#         #         description="Unauthorized"
#         #     )
#
#         file = request.FILES.get("file")
#
#         if not file:
#             return CustomResponse().errorResponse(
#                 data={},
#                 description="File is required"
#             )
#
#         try:
#
#             df = pd.read_excel(file)
#             required_columns = [
#                 "Grade",
#                 "Word",
#                 "Difficulty"
#             ]
#             missing_columns = [
#                 column
#                 for column in required_columns
#                 if column not in df.columns
#             ]
#
#             if missing_columns:
#
#                 return CustomResponse().errorResponse(
#                     data={},
#                     description=f"Missing columns: {', '.join(missing_columns)}"
#                 )
#
#             grades_map = {
#                 grade.name.strip().lower(): grade
#                 for grade in Grades.objects.filter(
#                     is_active=True
#                 )
#             }
#
#             existing_words = set(
#                 Words.objects.filter(
#                     is_active=True
#                 ).values_list(
#                     "word",
#                     flat=True
#                 )
#             )
#
#             words_to_create = []
#
#             skipped_count = 0
#
#             for _, row in df.iterrows():
#
#                 grade_name = str(
#                     row["Grade"]
#                 ).strip()
#
#                 word = str(
#                     row["Word"]
#                 ).strip()
#
#                 if not word:
#                     continue
#
#                 grade = grades_map.get(
#                     grade_name.lower()
#                 )
#
#                 if not grade:
#                     skipped_count += 1
#                     continue
#
#                 if word in existing_words:
#                     skipped_count += 1
#                     continue
#
#                 words_to_create.append(
#                     Words(
#                         grade=grade,
#                         word=word,
#                         difficulty=row.get("Difficulty",1),
#                         subject=row.get('Subject','English'),
#                         concept=row.get('Concept',None),
#                         hint=row.get('Hint',None),
#                         meaning=row.get("Meaning"),
#                         part_of_speech=row.get(
#                             "Part Of Speech"
#                         ),
#                         origin=row.get(
#                             "Origin"
#                         ),
#                         usage=row.get(
#                             "Usage"
#                         )
#                     )
#                 )
#
#                 existing_words.add(word)
#
#             Words.objects.bulk_create(
#                 words_to_create,
#                 batch_size=1000
#             )
#
#             return CustomResponse().successResponse(
#                 data={
#                     "created_count": len(words_to_create),
#                     "skipped_count": skipped_count
#                 },
#                 description="Words uploaded successfully"
#             )
#
#         except Exception as e:
#             return CustomResponse().errorResponse(
#                 data={},
#                 description=str(e)
#             )






class UploadWords(APIView):

    permission_classes = [AllowAny]

    parser_classes = [
        MultiPartParser,
        FormParser
    ]

    def post(self, request):

        file = request.FILES.get("file")

        if not file:
            return CustomResponse().errorResponse(
                data={},
                description="File is required."
            )

        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()

            required_columns = [
                "Grade",
                "Word",
                "Difficulty Level"
            ]

            missing_columns = [
                column for column in required_columns
                if column not in df.columns
            ]

            if missing_columns:
                return CustomResponse().errorResponse(
                    data={},
                    description=(
                        f"Missing required columns: "
                        f"{', '.join(missing_columns)}"
                    )
                )

            grades_map = {
                grade.name.strip().lower(): grade
                for grade in Grades.objects.filter(is_active=True)
            }

            existing_words = {
                (word.strip().lower(), str(grade_id))
                for word, grade_id in Words.objects.filter(
                    is_active=True
                ).values_list("word", "grade_id")
                if word
            }

            seen_in_file = set()
            words_to_create = []

            created_count = 0
            duplicate_count = 0
            invalid_grade_count = 0
            missing_word_count = 0

            duplicate_words = []
            invalid_grades = []
            missing_words = []

            def get_value(row, column, default=None):
                value = row.get(column, default)

                if pd.isna(value):
                    return default

                if isinstance(value, str):
                    value = value.strip()

                return value if value != "" else default

            for index, row in df.iterrows():

                excel_row = index + 2

                grade_value = get_value(row, "Grade")
                word_value = get_value(row, "Word")

                if grade_value is None:

                    invalid_grade_count += 1
                    invalid_grades.append({
                        "row": excel_row,
                        "grade": None
                    })
                    continue

                if word_value is None:

                    missing_word_count += 1
                    missing_words.append({
                        "row": excel_row
                    })
                    continue

                grade_name = str(grade_value).strip()
                word = str(word_value).strip().lower()

                grade = grades_map.get(grade_name.lower())

                if not grade:

                    invalid_grade_count += 1
                    invalid_grades.append({
                        "row": excel_row,
                        "grade": grade_name
                    })
                    continue

                duplicate_key = (word, str(grade.id))

                # Duplicate in uploaded Excel
                if duplicate_key in seen_in_file:

                    duplicate_count += 1
                    duplicate_words.append({
                        "row": excel_row,
                        "word": word,
                        "grade": grade.name,
                        "reason": "Duplicate in uploaded file"
                    })
                    continue

                seen_in_file.add(duplicate_key)

                # Duplicate already exists in database
                if duplicate_key in existing_words:

                    duplicate_count += 1
                    duplicate_words.append({
                        "row": excel_row,
                        "word": word,
                        "grade": grade.name,
                        "reason": "Already exists"
                    })
                    continue

                existing_words.add(duplicate_key)

                difficulty = get_value(
                    row,
                    "Difficulty Level",
                    1
                )

                try:
                    difficulty = int(float(difficulty))
                    if difficulty < 1 or difficulty > 5:
                        raise ValueError
                except (ValueError, TypeError):
                    return CustomResponse().errorResponse(
                        data={
                            "row": excel_row,
                            "difficulty": difficulty
                        },
                        description=(
                            "Difficulty Level must be between 1 and 5."
                        )
                    )

                points = get_value(row, "Points", 0)

                try:
                    points = int(float(points))
                    if points < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    return CustomResponse().errorResponse(
                        data={
                            "row": excel_row,
                            "points": points
                        },
                        description="Points must be a non-negative number."
                    )

                subject = get_value(row, "subject", "English")

                words_to_create.append(
                    Words(
                        grade=grade,
                        word=word,
                        meaning=get_value(
                            row, "Definition/ meaning"
                        ),
                        root_word=get_value(
                            row, "Root word"
                        ),
                        phonetic_script=get_value(
                            row, "Phonetic script"
                        ),
                        syllabified_stressed_transcript=get_value(
                            row, "Syllabified Stressed Transcript"
                        ),
                        concept=get_value(
                            row, "Concept name"
                        ),
                        origin=get_value(
                            row, "Origin"
                        ),
                        origin_word=get_value(
                            row, "Origin Word (Exact Word)"
                        ),
                        origin_word_meaning=get_value(
                            row, "Origin Word Meaning"
                        ),
                        usage=get_value(
                            row, "Usage"
                        ),
                        hint=get_value(
                            row, "Hint"
                        ),
                        antonym=get_value(
                            row, "Antonym"
                        ),
                        synonym=get_value(
                            row, "Synonym"
                        ),
                        part_of_speech=get_value(
                            row, "Parts Of Speech"
                        ),
                        difficulty=difficulty,
                        points=points,
                        word_status=get_value(
                            row, "Status"
                        ),
                        domain=get_value(
                            row, "Domain"
                        ),
                        subject=subject
                    )
                )

                created_count += 1

            with transaction.atomic():

                if words_to_create:
                    Words.objects.bulk_create(
                        words_to_create,
                        batch_size=1000
                    )

            return CustomResponse().successResponse(
                data={
                    "summary": {
                        "total_rows": len(df),
                        "created_count": created_count,
                        "duplicate_count": duplicate_count,
                        "invalid_grade_count": invalid_grade_count,
                        "missing_word_count": missing_word_count
                    },
                    "duplicate_words": duplicate_words,
                    "invalid_grades": invalid_grades,
                    "missing_words": missing_words
                },
                description="Words uploaded successfully."
            )

        except IntegrityError:

            return CustomResponse().errorResponse(
                data={},
                description=(
                    "Upload failed because duplicate words already exist. "
                    "Please verify the Excel file and try again."
                )
            )

        except Exception as e:

            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )




class DashboardAPIView(APIView):

    def get(self, request):
        today = timezone.localdate()
        total_users = UserMaster.objects.count()
        total_words = Words.objects.count()
        audio_generated = WordAudios.objects.count()
        audio_pending = max(
            total_words - audio_generated,
            0
        )
        total_word_attempts = PracticeAttempts.objects.count()
        daily_active_users = PracticeAttempts.objects.filter(
            created_at__date=today
        ).values(
            "kid"
        ).distinct().count()
        return CustomResponse().successResponse(data={
                "total_users": total_users,
                "total_words": total_words,
                "audio_generated": audio_generated,
                "audio_pending": audio_pending,
                "total_word_attempts": total_word_attempts,
                "daily_active_users": daily_active_users
        })


class SubjectCrud(APIView):

    def post(self, request):
        name = request.data.get("name", "").strip()
        description = request.data.get("description")
        icon = request.data.get("icon")
        color_code = request.data.get("color_code", "#4F46E5")
        display_order = request.data.get("display_order", 0)

        if not name:
            return CustomResponse().errorResponse(
                description="Subject name is required."
            )

        if Subjects.objects.filter(
            name__iexact=name,
        ).exists():
            return CustomResponse().errorResponse(
                description="Subject already exists."
            )

        subject = Subjects.objects.create(
            name=name,
            description=description,
            icon=icon,
            color_code=color_code,
            display_order=display_order
        )

        return CustomResponse().successResponse(
            data={
                "id": subject.id
            },
            description="Subject created successfully."
        )

    def get(self, request):

        subjects = Subjects.objects.all().order_by(
            "display_order",
            "name"
        )

        data = []

        for subject in subjects:
            data.append({
                "id": subject.id,
                "name": subject.name,
                "description": subject.description,
                "icon": subject.icon,
                "color_code": subject.color_code,
                "display_order": subject.display_order,
                "is_active": subject.is_active
            })

        return CustomResponse().successResponse(data=data)

class SubjectDeleteAPIView(APIView):
    def delete(self, request, subject_id):
        subject = Subjects.objects.filter(
            id=subject_id
        ).first()
        if not subject:
            return CustomResponse().errorResponse(
                description="Subject not found."
            )
        if subject.words.exists():
            return CustomResponse().errorResponse(
                description="This subject cannot be deleted because it is associated with one or more words."
            )
        subject.delete()
        return CustomResponse().successResponse(
            data={},
            description="Subject deleted successfully."
        )