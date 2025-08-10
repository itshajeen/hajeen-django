from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import Guardian, Dependent 

# Create your models here.


# MessageType Model
class MessageType(models.Model):
    """Model to define different types of messages."""
    label = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[('active', _('Active')), ('inactive', _('Inactive'))], default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label
    

# Message Model 
class Message(models.Model):
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='received_messages')
    dependent = models.ForeignKey(Dependent, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.guardian} -> {self.dependent}: {self.message_type} ({self.created_at})"
    
