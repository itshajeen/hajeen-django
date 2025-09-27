import random
from datetime import date, timedelta

from django.conf import settings
from fcm_django.models import FCMDevice
from django.utils.translation import gettext_lazy as _ 
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from core.pagination import DefaultPagination
from core.permissions import IsAdminOrReadOnly, IsGuardianOwnDependent
from core.utils import TaqnyatSMSService
from message.models import GuardianMessageType, Message, MessageType 
from .models import AppSettings, Dependent, DisabilityType, Guardian, GuardianMessageDefault, User 
from .serializers import AppSettingsSerializer, DependentSerializer, DisabilityTypeSerializer, GuardianSerializer, PhoneLoginSerializer, PhonePasswordLoginSerializer, SetGuardianPinCodeSerializer, UserProfileSerializer, UserProfileUpdateSerializer


# Phone Login API View
class PhoneLoginAPIView(APIView):
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Return OTP in response (for development/testing purposes)
            return Response({
                'detail': _('تم إرسال OTP بنجاح.'),
                'role': user.role,
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
                'detail': _('تم تسجيل الدخول بنجاح.'),
                'access_token': access_token,
                'refresh_token': refresh_token
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPAPIView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')

        # get registration id from token 
        registration_id = request.headers.get("X-Client-Fcm-Token")
        device_type = request.headers.get("Device-Type", "ios")  # Optional 

        if not phone_number or not otp:
            return Response({'detail': _('رقم الهاتف وكلمة المرور لمرة واحدة مطلوبان.')}, status=400)

        try:
            user = User.objects.get(phone_number=phone_number)
            
            if user.otp == otp:
                # Set Otp 
                user.otp = None
                user.save()

                # create JWT Token 
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                # update or create registration id 
                if registration_id:
                    FCMDevice.objects.update_or_create(
                        user=user,
                        registration_id=registration_id,
                        defaults={"type": device_type}
                    )

                return Response({
                    'detail': _('تم تسجيل الدخول بنجاح.'),
                    'role': user.role,
                    'access_token': access_token,
                    'refresh_token': refresh_token
                })

            else:
                return Response({'detail': _('كلمة مرور لمرة واحدة غير صالحة.')}, status=400)

        except User.DoesNotExist:
            return Response({'detail': _('المستخدم غير موجود.')}, status=404)


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
            return Response({"message" : _("تم تحديث الحساب بنجاح"), "data" : serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Account 
class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": _("تم حذف الحساب بنجاح.")}, status=status.HTTP_204_NO_CONTENT)


# Guardian Set Pin Code API View 
class SetGuardianPinCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetGuardianPinCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('تم تعيين رمز PIN بنجاح.')}, status=201)
        return Response(serializer.errors, status=400)


# Request Guardian PIN Reset API View 
class RequestGuardianPinResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'guardian':
            return Response({'detail': _('يمكن للمشرفين فقط طلب إعادة تعيين الرقم السري.')}, status=403)

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({'detail': _('المشرف غير موجود.')}, status=404)

        otp = str(random.randint(1000, 9999))
        guardian.pin_reset_otp = otp
        guardian.otp_created_at = timezone.now()
        guardian.save()

        # Send SMS via Taqnyat
        sms_service = TaqnyatSMSService()
        sms_service.send_sms(
            recipients=[user.phone_number],
            message = f"عزيزنا العميل،\nرمز التحقق لتغيير الكود السري الخاص بمنصة شركة رزان عدنان المليك للتجارة هو {otp}", 
            sender_name=settings.TAQNYAT_SENDER_NAME 
        )
        return Response({'detail': _('لقد تم إرسال رمز التحقق إلى رقم هاتفك بنجاح.'), 'otp': guardian.pin_reset_otp }, status=200)


# Reset Guardian PIN Code API View
class ResetGuardianPinCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'guardian':
            return Response({'detail': _('يمكن للمشرفين فقط إعادة تعيين الرمز البريدي.')}, status=403)

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({'detail': _('المشرف غير مسجل')}, status=404)

        otp = request.data.get('otp')
        new_pin_code = request.data.get('new_pin_code')

        # Check OTP
        if guardian.pin_reset_otp != otp:
            return Response({'detail': _('الرمز البريدي او رمز التحقق غير صحيح')}, status=400)

        # Validate new_pin_code (example: must be 4 digits)
        if not new_pin_code or not new_pin_code.isdigit() or len(new_pin_code) != 4:
            return Response({'detail': _('الرمز البريدي او رمز التحقق غير صحيح')}, status=400)

        guardian.set_code(new_pin_code)
        guardian.pin_reset_otp = None
        guardian.otp_created_at = None
        guardian.save()

        return Response({'detail': _('تم إعادة تعيين الرمز البريدي بنجاح.')}, status=200)
    

# Verify Guardian PIN Code API View
class VerifyGuardianPinCodeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        if user.role != 'guardian':
            return Response({'detail': _('يمكن للمشرفين فقط التحقق من الرمز البريدي.')}, status=403)
        
        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({'detail': _('المشرف غير موجود.')}, status=404)
        
        pin_code = request.data.get('pin_code')
        if not pin_code or not guardian.check_code(pin_code):
            return Response({'detail': _('الرمز البريدي غير صالح.'), 'is_verified': False}, status=400)

        # get registration id from headers  
        registration_id = request.headers.get("X-Client-Fcm-Token")
        device_type = request.headers.get("Device-Type", "ios") # Default to ios 

        if registration_id:
            FCMDevice.objects.update_or_create(
                user=user,
                registration_id=registration_id,
                defaults={"type": device_type}
            )

        # If pin_code is valid, return success response
        return Response({
            'detail': _('تم التحقق من الرمز البريدي بنجاح.'),
            'is_verified': True
        }, status=200)
    

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

    # Update Messages 
    @action(detail=True, methods=['post'], url_path='update-messages')
    def update_messages(self, request, pk=None):
        guardian = self.get_object()
        try:
            guardian_default = guardian.message_defaults
        except GuardianMessageDefault.DoesNotExist:
            return Response(
                {"detail": _("لا يوجد سجل رسالة افتراضي لهذا المشرف")},
                status=status.HTTP_404_NOT_FOUND
            )

        new_count = request.data.get("messages_per_month")
        if new_count is None:
            return Response({"detail": _("عدد الرسائل في الشهر مطلوبة")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_count = int(new_count)
        except ValueError:
            return Response({"detail": _("عدد الرسائل يجب ان يكون عدد صحيح")}, status=status.HTTP_400_BAD_REQUEST)

        guardian_default.messages_per_month = new_count
        guardian_default.save()

        return Response(
            {
                "guardian": guardian.user.name,
                "messages_per_month": guardian_default.messages_per_month
            },
            status=status.HTTP_200_OK
        )


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
    queryset = Dependent.objects.all()
    serializer_class = DependentSerializer
    permission_classes = [IsGuardianOwnDependent, IsAdminUser]
    pagination_class = DefaultPagination

    def get_queryset(self):
        user = self.request.user
        if user.role == 'guardian':
            # If the user is a guardian, filter dependents by their guardian
            return super().get_queryset().filter(guardian__user=user).order_by('-date_birth')
        elif user.role == 'admin':
            # If the user is an admin, return all dependents
            return super().get_queryset().order_by('-date_birth')
        else:
            # For other roles, return an empty queryset
            return Dependent.objects.none()
        
    
    # Register Device for Push Notifications 
    @action(detail=True, methods=['post'], url_path='register-device')
    def register_device(self, request, pk=None):
        dependent = self.get_object()
        registration_id = request.data.get("registration_id")

        if not registration_id:
            return Response(
                {"detail": _("معرف التسجيل مطلوب")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Unbind any other dependent that has the same registration_id
        Dependent.objects.filter(registration_id=registration_id).exclude(pk=dependent.pk).update(registration_id=None)

        # Bind the current dependent to the device
        dependent.registration_id = registration_id
        dependent.save()

        return Response(
            {"message": _("تم تسجيل الجهاز بنجاح وربطه بالتابع الحالي")},
            status=status.HTTP_200_OK
        )



# App Settings View 
class AppSettingsView(APIView):
    def get_object(self):
        # App Settings 
        obj = AppSettings.objects.first()
        if not obj:
            obj = AppSettings.objects.create()
        return obj

    def get(self, request):
        settings_instance = self.get_object()
        serializer = AppSettingsSerializer(settings_instance)
        return Response(serializer.data)

    def post(self, request):
        settings_instance = self.get_object()
        
        update_now = request.data.get('update_guardians_now', False)
        update_next_month = request.data.get('update_guardians_next_month', False)

        old_max = settings_instance.max_sms_message

        serializer = AppSettingsSerializer(settings_instance, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            new_max = instance.max_sms_message
            diff = new_max - old_max

            if diff > 0:
                if update_now:
                    # Immediately adjust the balance
                    for guardian_default in GuardianMessageDefault.objects.filter(app_settings=instance):
                        guardian_default.messages_per_month += diff
                        if guardian_default.messages_per_month > new_max:
                            guardian_default.messages_per_month = new_max
                        guardian_default.save()

                if update_next_month:
                    # Save the difference to apply it at the beginning of the new month
                    instance.pending_guardian_increment = diff
                    instance.save(update_fields=['pending_guardian_increment'])

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Dashboard Stats View 
class DashboardStatsView(APIView):
    """
    Dashboard statistics view (filter by date range)
    """

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()

        # Get start date and end date 
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Convert date 
        if start_date:
            start_date = date.fromisoformat(start_date)  # format: YYYY-MM-DD
        if end_date:
            end_date = date.fromisoformat(end_date)

        # Filter Querysets 
        messages_qs = Message.objects.all()
        users_qs = User.objects.all()
        dependents_qs = Dependent.objects.all()
        guardian_msgtype_qs = GuardianMessageType.objects.all()
        msgtype_qs = MessageType.objects.all()

        if start_date and end_date:
            messages_qs = messages_qs.filter(created_at__date__range=[start_date, end_date])
            users_qs = users_qs.filter(date_joined__date__range=[start_date, end_date]) if hasattr(User, "date_joined") else users_qs
            dependents_qs = dependents_qs.filter(created_at__date__range=[start_date, end_date])
            guardian_msgtype_qs = guardian_msgtype_qs.filter(guardian__created_at__date__range=[start_date, end_date])

        elif start_date:
            messages_qs = messages_qs.filter(created_at__date=start_date)
            users_qs = users_qs.filter(date_joined__date=start_date) if hasattr(User, "date_joined") else users_qs
            dependents_qs = dependents_qs.filter(created_at__date=start_date)
            guardian_msgtype_qs = guardian_msgtype_qs.filter(guardian__created_at__date=start_date)

        # Total Users 
        total_users = users_qs.count()

        # Total Messages 
        total_messages = messages_qs.count()
        today_messages = messages_qs.filter(created_at__date=today).count()

        # Messages according to month 
        messages_by_month = (
            messages_qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        # Average dependents age 
        dependents = dependents_qs.exclude(date_birth=None)
        ages = [
            (date.today().year - d.date_birth.year)
            - ((date.today().month, date.today().day) < (d.date_birth.month, d.date_birth.day))
            for d in dependents
        ]
        average_age = sum(ages) / len(ages) if ages else 0

        # sos requests count 
        sos_requests = messages_qs.filter(is_emergency=True).count()

        # Demographic distribution
        gender_distribution = dependents_qs.values("gender").annotate(count=Count("id"))
        marital_distribution = dependents_qs.values("marital_status").annotate(count=Count("id"))

        # Communication statistics
        total_interactions = messages_qs.count()
        text_messages = messages_qs.filter(is_sms=True).count()
        voice_messages = messages_qs.filter(is_voice=True).count()

        # Count how many times each message type was linked to guardians
        activation_counts = guardian_msgtype_qs.values(
            "message_type__id", "message_type__label_en", "message_type__label_ar"
        ).annotate(activation_count=Count("id"))

        # Count how many times messages of each type were sent
        sent_counts = messages_qs.filter(message_type__isnull=False).values(
            "message_type__message_type__id",
            "message_type__message_type__label_en",
            "message_type__message_type__label_ar"
        ).annotate(sent_count=Count("id"))

        # Merge activation and sent counts by message type
        msgtype_stats = []
        sent_lookup = {
            (s["message_type__message_type__id"]): s["sent_count"]
            for s in sent_counts
        }
        for item in activation_counts:
            msg_id = item["message_type__id"]
            msgtype_stats.append({
                "id": msg_id,
                "label_en": item["message_type__label_en"],
                "label_ar": item["message_type__label_ar"],
                "activation_count": item["activation_count"],
                "sent_count": sent_lookup.get(msg_id, 0)
            })

        data = {
            "users": {
                "total": total_users,
            },
            "messages": {
                "total": total_messages,
                "today": today_messages,
                "by_month": list(messages_by_month),
            },
            "age": {
                "average": round(average_age, 2),
            },
            "sos": sos_requests,
            "demographics": {
                "gender": list(gender_distribution),
                "marital": list(marital_distribution),
            },
            "communication": {
                "total_interactions": total_interactions,
                "text_messages": text_messages,
                "voice_messages": voice_messages,
            },
            "message_types": msgtype_stats,  
        }

        return Response(data)


