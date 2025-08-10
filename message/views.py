from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser 
from core.pagination import DefaultPagination
from .models import MessageType 
from .serializers import MessageTypeSerializer 


# MessageType ViewSet 
class MessageTypeViewSet(viewsets.ModelViewSet):
    queryset = MessageType.objects.all()
    serializer_class = MessageTypeSerializer
    permission_classes = [IsAdminUser]  # Only admins can manage message types 
    pagination_class = DefaultPagination  # Disable pagination for simplicity 
