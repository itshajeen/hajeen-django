from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from core.pagination import DefaultPagination
from .models import MessageType, Message
from .serializers import MessageTypeSerializer, MessageSerializer


# MessageType ViewSet 
class MessageTypeViewSet(viewsets.ModelViewSet):
    queryset = MessageType.objects.all()
    serializer_class = MessageTypeSerializer
    permission_classes = [IsAdminUser]  # Only admins can manage message types 
    pagination_class = DefaultPagination  # Disable pagination for simplicity 


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

    