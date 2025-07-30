import random
from django.utils.translation import gettext_lazy as _ 
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

from core.pagination import DefaultPagination
from core.permissions import IsAdminOrReadOnly, IsGuardianOwnDependent
from core.utils import send_sms
from .models import Dependent, DisabilityType, Guardian, User 
from .serializers import DependentSerializer, DisabilityTypeSerializer, GuardianSerializer, PhoneLoginSerializer, PhonePasswordLoginSerializer, SetGuardianPinCodeSerializer, UserProfileSerializer, UserProfileUpdateSerializer


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


# Guardian Set Pin Code API View 
class SetGuardianPinCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetGuardianPinCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('PIN code set successfully.')}, status=201)
        return Response(serializer.errors, status=400)


# Request Guardian PIN Reset API View 
class RequestGuardianPinResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'guardian':
            return Response({'detail': _('Only guardians can request pin reset.')}, status=403)

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({'detail': 'Guardian not found.'}, status=404)

        otp = str(random.randint(100000, 999999))
        guardian.pin_reset_otp = otp
        guardian.otp_created_at = timezone.now()
        guardian.save()

        # Send SMS
        send_sms(
            recipients=[user.phone_number],
            body=f"رمز التحقق لتغيير الكود السري هو: {otp}",
            sender="Hajeen"
        )
        return Response({'detail': _('Verification code has been sent to your phone number successfully.'), 'otp': guardian.pin_reset_otp }, status=200)


# Reset Guardian PIN Code API View
class ResetGuardianPinCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'guardian':
            return Response({'detail': _('Only guardians can reset pin code.')}, status=403)

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({'detail': 'Guardian not found.'}, status=404)

        otp = request.data.get('otp')
        new_pin_code = request.data.get('new_pin_code')

        # Check OTP
        if guardian.pin_reset_otp != otp:
            return Response({'detail': _('Invalid OTP or PIN code.')}, status=400)

        # Validate new_pin_code (example: must be 4 digits)
        if not new_pin_code or not new_pin_code.isdigit() or len(new_pin_code) != 4:
            return Response({'detail': _('Invalid OTP or PIN code.')}, status=400)

        guardian.set_code(new_pin_code)
        guardian.pin_reset_otp = None
        guardian.otp_created_at = None
        guardian.save()

        return Response({'detail': _('PIN code reset successfully.')}, status=200)
    

# Guardian Viewset 
class GuardianViewSet(viewsets.ModelViewSet):
    queryset = Guardian.objects.select_related('user').all()
    serializer_class = GuardianSerializer 
    permission_classes = [IsAdminUser]
    pagination_class = DefaultPagination 

    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='toggle-block')
    def toggle_block(self, request, pk=None):
        guardian = self.get_object()
        user = guardian.user
        user.is_block = not user.is_block
        user.save()
        return Response({'status': 'success', 'is_block': user.is_block}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-activate')
    def toggle_activate(self, request, pk=None):
        guardian = self.get_object()
        user = guardian.user
        user.is_active = not user.is_active
        user.save()
        return Response({'status': 'success', 'is_active': user.is_active}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        # Delete the Guardian and associated User 
        user = instance.user
        instance.delete()
        user.delete()


# Disability Type Viewset
class DisabilityTypeViewSet(viewsets.ModelViewSet):
    queryset = DisabilityType.objects.all()
    serializer_class = DisabilityTypeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = DefaultPagination

    def get_queryset(self):
        queryset = super().get_queryset().order_by('name_en')
        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(status='active') # check if user is not staff, then filter active disability types
        return queryset


# Dependent Viewset 
class DependentViewSet(viewsets.ModelViewSet):
    queryset = Dependent.objects.select_related('guardian').all()
    serializer_class = DependentSerializer
    permission_classes = [IsGuardianOwnDependent]
    pagination_class = DefaultPagination

    def get_queryset(self):
        return super().get_queryset().order_by('-date_birth')
