from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters 
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from core.models import Dependent
from core.pagination import DefaultPagination
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

    def create(self, request, *args, **kwargs):
        registration_id = request.data.get('registration_id')
        message_type_id = request.data.get('message_type_id')
        is_sms = request.data.get('is_sms', False)
        is_emergency = request.data.get('is_emergency', False)

        # registration_id is always required
        if not registration_id:
            return Response(
                {"detail": _("registration_id is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get dependent and guardian
        dependent = get_object_or_404(Dependent, registration_id=registration_id)
        guardian = dependent.guardian

        message_type = None
        if is_emergency:
            if message_type_id:
                return Response(
                    {"detail": _("Emergency messages should not have a message_type_id.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            if not message_type_id:
                return Response(
                    {"detail": _("message_type_id is required for non-emergency messages.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
            message_type = get_object_or_404(GuardianMessageType, id=message_type_id)

        # Create message
        message = Message.objects.create(
            guardian=guardian,
            dependent=dependent,
            message_type=message_type,
            is_sms=is_sms,
            is_emergency=is_emergency
        )

        serializer = self.get_serializer(message)
        return Response(
            {"message": _('Message sent successfully'), "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    def get_queryset(self):
        guardian = getattr(self.request.user, 'guardian', None)
        if guardian:
            return self.queryset.filter(guardian=guardian)
        return self.queryset.none()
    

# GuardianMessagesAPIView to get messages for a guardian 
class GuardianMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'guardian' or not hasattr(user, 'guardian'):
            return Response({"detail": _("Not authorized.")}, status=403)

        guardian = user.guardian
        dependent_id = request.query_params.get('dependent_id')

        # Get all messages for the guardian 
        messages = guardian.received_messages.all().select_related('dependent', 'message_type')

        # Filter by dependent if provided 
        if dependent_id:
            messages = messages.filter(dependent_id=dependent_id)

        # Distribute messages into new and previous based on is_seen status 
        new_messages = messages.filter(is_seen=False).order_by('-created_at')
        previous_messages = messages.filter(is_seen=True).order_by('-created_at')

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
