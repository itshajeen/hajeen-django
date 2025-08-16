from rest_framework import viewsets, status, filters 
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import IsAdminUser, IsAuthenticated
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
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination  # Use custom pagination class
    
    def get_queryset(self):
        guardian = self.request.user.guardian
        # Filter messages by the guardian associated with the authenticated user 
        if guardian:
            return self.queryset.filter(guardian=guardian)
        return self.queryset.none()

    