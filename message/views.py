from rest_framework import viewsets
from core.permissions import IsGuardianOwnDependent 
from .models import MessageType 
from .serializers import MessageTypeSerializer 


# MessageType ViewSet 
class MessageTypeViewSet(viewsets.ModelViewSet):
    queryset = MessageType.objects.all()
    serializer_class = MessageTypeSerializer
    permission_classes = [IsGuardianOwnDependent]  # Only allow guardians to manage their own message types 

    def get_queryset(self):
        guardian = self.request.user.guardian
        if guardian:
            return self.queryset.filter(guardian=guardian)
        return self.queryset.none()  # Return empty queryset if no guardian found