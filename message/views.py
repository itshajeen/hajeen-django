from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.timezone import is_naive, make_aware
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters 
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from core.models import Dependent
from core.pagination import DefaultPagination
from core.utils import send_notification_to_user, TaqnyatSMSService
from message.permissions import IsAdminOrReadOnly
from .models import GuardianMessageType, MessageType, Message
from .serializers import GuardianMessageTypeBulkUpsertSerializer, GuardianMessageTypeSerializer, MessageTypeSerializer, MessageSerializer


# MessageType ViewSet 
class MessageTypeViewSet(viewsets.ModelViewSet):
    queryset = MessageType.objects.all()
    serializer_class = MessageTypeSerializer
    permission_classes = [IsAdminOrReadOnly]  # Only admins can manage message types 
    pagination_class = DefaultPagination  # Disable pagination for simplicity 
    filter_backends = [filters.SearchFilter]
    search_fields = ['label_en', 'label_ar'] 


# GuardianMessageType ViewSet 
class GuardianMessageTypeViewSet(viewsets.ModelViewSet):
    queryset = GuardianMessageType.objects.all()
    serializer_class = GuardianMessageTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['message_type__label_en', 'message_type__label_ar']

    def get_queryset(self):
        guardian = getattr(self.request.user, 'guardian', None)
        return self.queryset.filter(guardian=guardian) if guardian else self.queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = GuardianMessageTypeBulkUpsertSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        return Response(serializer.to_representation(instances), status=status.HTTP_201_CREATED)


# Message ViewSet 
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    http_method_names = ['get', 'post']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        guardian = getattr(self.request.user, 'guardian', None)
        if guardian:
            return self.queryset.filter(guardian=guardian).select_related(
                'dependent', 'message_type', 'message_type__message_type'
            )
        return self.queryset.none()
    
    def create(self, request, *args, **kwargs):
        registration_id = request.data.get('registration_id')
        message_type_id = request.data.get('message_type_id')
        is_sms = request.data.get('is_sms', False)
        is_voice = request.data.get('is_voice', False)
        is_emergency = request.data.get('is_emergency', False)

        if not registration_id:
            return Response({"detail": _("registration_id is required.")}, status=status.HTTP_400_BAD_REQUEST)

        dependent = get_object_or_404(Dependent, registration_id=registration_id)
        guardian = dependent.guardian

        if is_sms and is_voice:
            return Response({"detail": _("A message cannot be both SMS and Voice.")}, status=status.HTTP_400_BAD_REQUEST)

        message_type = None

        if is_emergency:
            if message_type_id:
                return Response({"detail": _("Emergency messages should not have a message_type_id.")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not message_type_id:
                return Response({"detail": _("message_type_id is required for non-emergency messages.")}, status=status.HTTP_400_BAD_REQUEST)
            
            message_type = GuardianMessageType.objects.filter(id=message_type_id, guardian=guardian).first()
            if not message_type:
                return Response({"detail": _("This message_type does not belong to the guardian.")}, status=status.HTTP_400_BAD_REQUEST)

        message = Message(
            guardian=guardian,
            dependent=dependent,
            message_type=message_type,
            is_sms=is_sms,
            is_voice=is_voice,
            is_emergency=is_emergency
        )
        try:
            message.full_clean()
            message.save()
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        if message.is_emergency:
            title = f"رسالة طارئة من {dependent.name}"
            notification_body = f"رسالة طارئة من {dependent.name}"

        elif message_type and message_type.message_type:
            title = f"{message_type.message_type.label_ar} من {dependent.name}"
            notification_body = f"{message_type.message_type.label_ar} \n من {dependent.name} \n تطبيق هجين"
        else:
            title = f"رسالة جديدة من {dependent.name}"
            notification_body = f"رسالة جديدة من {dependent.name}"

        send_notification_to_user(
            user=guardian.user,
            title=title,
            body=notification_body,
            data={"type": "new_message", "message_id": str(message.id), "dependent_id": str(dependent.id)}
        )

        if is_sms and guardian.user.phone_number:
            sms_service = TaqnyatSMSService()
            sms_service.send_sms(
                recipients=[guardian.user.phone_number],
                message=f"{message_type.message_type.label_ar if message_type else 'لديك رسالة جديدة'} \n من {dependent.name} \n تطبيق هجين \n \n شركة رزان عدنان المليك للتجارة ",
                sender_name=settings.TAQNYAT_SENDER_NAME 
            )

        serializer = self.get_serializer(message)
        return Response({"message": _("Message sent successfully"), "data": serializer.data}, status=status.HTTP_201_CREATED)


# GuardianMessagesAPIView
class GuardianMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'guardian' or not hasattr(user, 'guardian'):
            return Response({"detail": _("Not authorized.")}, status=403)

        guardian = user.guardian
        dependent_id = request.query_params.get('dependent_id')

        messages = guardian.received_messages.all().select_related(
            'dependent', 'message_type', 'message_type__message_type'
        )

        if dependent_id:
            messages = messages.filter(dependent_id=dependent_id)

        now = timezone.now()
        ten_minutes_ago = now - timedelta(minutes=10)
        if is_naive(ten_minutes_ago):
            ten_minutes_ago = make_aware(ten_minutes_ago)

        new_messages = messages.filter(created_at__gte=ten_minutes_ago).order_by('-created_at')
        previous_messages = messages.filter(created_at__lt=ten_minutes_ago).order_by('-created_at')

        def serialize_message(msg):
            if msg.is_emergency:
                label = _("Emergency Message")
            elif msg.message_type:
                label = msg.message_type.message_type.label_ar
            else:
                label = _("Unknown")
            return {
                "id": msg.id,
                "dependent_name": msg.dependent.name,
                "message_label": label,
                "created_at": msg.created_at.strftime('%Y/%m/%d %I:%M%p'),
            }

        return Response({
            "new": [serialize_message(m) for m in new_messages],
            "previous": [serialize_message(m) for m in previous_messages],
        })
    

# MarkMessagesReadAPIView to mark messages as read 
class MarkMessagesReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get the guardian profile 
        guardian = getattr(request.user, 'guardian', None)
        if not guardian:
            return Response({'detail': _('Guardian profile not found.')}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the dependent_id from request data 
        dependent_id = request.data.get('dependent_id')
        queryset = Message.objects.filter(guardian=guardian, is_seen=False)
        if dependent_id:
            queryset = queryset.filter(dependent_id=dependent_id)
        
        # Update the messages to mark them as read 
        updated_count = queryset.update(is_seen=True)
        return Response({
            'message': f'{updated_count} messages marked as read.'
        }, status=status.HTTP_200_OK)
