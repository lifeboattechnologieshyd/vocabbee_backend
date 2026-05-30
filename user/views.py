from rest_framework.views import APIView
from rest_framework.response import Response


class TestAPIView(APIView):
    def get(self, request):
        return Response({"status": "success", "message": "user test API works"})