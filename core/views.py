from django.utils.translation import gettext_lazy as _ 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

from core.pagination import DefaultPagination
from core.permissions import IsAdminOrReadOnly
from .models import Follower, User 
from .serializers import FollowerSerializer, PhoneLoginSerializer, PhonePasswordLoginSerializer, UserProfileSerializer, UserProfileUpdateSerializer


# Phone Login API View
class PhoneLoginAPIView(APIView):
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Return OTP in response (for development/testing purposes)
            return Response({
                'detail': _('OTP sent successfully.'),
                'role': user.role,
                'otp': user.otp  # Return the OTP here
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Phone Password Login API View for superusers and admins 
class PhonePasswordLoginAPIView(APIView):
    def post(self, request):
        serializer = PhonePasswordLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({
                'detail': _('Login successful.'),
                'access_token': access_token,
                'refresh_token': refresh_token
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Verify OTP API View 
class VerifyOTPAPIView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')

        try:
            user = User.objects.get(phone_number=phone_number)
            if user.otp == otp:
                # Reset OTP if needed
                user.otp = None
                user.save()

                # Generate tokens
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                return Response({
                    'detail': _('Login successful.'),
                    'role': user.role,
                    'is_craftsman': user.is_craftsman,
                    'is_client': user.is_client,
                    'access_token': access_token,
                    'refresh_token': refresh_token
                })
            else:
                return Response({'detail': _('Invalid OTP.')}, status=400)
        except User.DoesNotExist:
            return Response({'detail': _('User not found.')}, status=404)
        

# User Profile API View 
class UserProfileAPIView(APIView):
    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message" : _("profile updated successfully"), "data" : serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Account 
class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": _("Account deleted successfully.")}, status=status.HTTP_204_NO_CONTENT)
    


# Craftsman Viewset 
class FollowerViewSet(viewsets.ModelViewSet):
    queryset = Follower.objects.select_related('user').all()
    serializer_class = FollowerSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

    @action(detail=True, methods=['post'])
    def toggle_block(self, request, pk=None):
        craftsman = self.get_object()
        user = craftsman.user
        user.is_block = not user.is_block
        user.save()
        return Response({'status': 'success', 'is_block': user.is_block}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-activate')
    def toggle_activate(self, request, pk=None):
        craftsman = self.get_object()
        user = craftsman.user
        user.is_active = not user.is_active
        user.save()
        return Response({'status': 'success', 'is_active': user.is_active}, status=status.HTTP_200_OK)




