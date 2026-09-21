from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Student

class LoginView(APIView):
    def post(self, request):
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Parolni kiriting'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            student = Student.objects.get(token=password, is_active=True)
            return Response({'token': student.token})
        except Student.DoesNotExist:
            return Response({'error': 'Noto\'g\'ri parol yoki faol emas'}, status=status.HTTP_401_UNAUTHORIZED)
