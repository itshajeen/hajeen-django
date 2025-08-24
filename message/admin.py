from django.contrib import admin
from .models import Message, MessageType, GuardianMessageType 

# Register your models here.
admin.site.register(Message)
admin.site.register(MessageType)
admin.site.register(GuardianMessageType)