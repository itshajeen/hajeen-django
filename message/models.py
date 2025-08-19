from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import Guardian, Dependent 
import os
from django.utils.text import slugify
from uuid import uuid4

# Create your models here.


# MessageType Model
class MessageType(models.Model):
    """Model to define different types of messages."""

    def rename_audio_file_ar(instance, filename):
        base, ext = os.path.splitext(filename)
        safe_name = slugify(base)[:50]  # Split first 50 chars 
        return f"audio_messages/ar/{uuid4().hex}_{safe_name}{ext}"

    def rename_audio_file_en(instance, filename):
        base, ext = os.path.splitext(filename)
        safe_name = slugify(base)[:50]
        return f"audio_messages/en/{uuid4().hex}_{safe_name}{ext}"

    label_ar = models.CharField(max_length=100)
    label_en = models.CharField(max_length=100)
    audio_file_ar = models.FileField(
        upload_to=rename_audio_file_ar, 
        max_length=255, 
        blank=True, 
        null=True
    )

    audio_file_en = models.FileField(
        upload_to=rename_audio_file_en, 
        max_length=255, 
        blank=True, 
        null=True   
    )
    status = models.CharField(max_length=20, choices=[('active', _('Active')), ('inactive', _('Inactive'))], default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label
    

# GuardianMessageType Model 
class GuardianMessageType(models.Model):
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="guardian_messages")
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE, related_name="guardian_messages")

    class Meta:
        unique_together = ('guardian', 'message_type')  
    def __str__(self):
        return f"{self.guardian.user.phone_number} - {self.message_type.label_en}"


# Message Model 
class Message(models.Model):
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='received_messages')
    dependent = models.ForeignKey(Dependent, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.ForeignKey(GuardianMessageType, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)
    is_sms = models.BooleanField(default=False)
    is_voice = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False)


    def clean(self):
        if not self.is_emergency and not self.message_type:
            raise ValidationError("message_type is required for non-emergency messages.")
        if self.is_emergency and self.message_type:
            raise ValidationError("Emergency messages should not have a message_type.")

    def __str__(self):
        return f"{self.guardian} -> {self.dependent}: {self.message_type} ({self.created_at})"
    
