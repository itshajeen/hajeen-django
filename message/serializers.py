from rest_framework import serializers 
from django.utils.translation import gettext_lazy as _
from .models import MessageType, Message 


# MessageType Serializer 
class MessageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageType
        fields = ['id', 'label', 'guardian']
        read_only_fields = ['guardian']  # Guardian is set automatically based on request user  

    def create(self, validated_data):
        guardian = self.context['request'].user.guardian
        if not guardian:
            raise serializers.ValidationError({'detail': _('Guardian profile not found.')})
        return MessageType.objects.create(guardian=guardian, **validated_data)
        

# Message Serializer
class MessageSerializer(serializers.ModelSerializer):
    dependent_name = serializers.CharField(source='dependent.name', read_only=True)
    guardian_name  = serializers.CharField(source='guardian.username', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id',
            'guardian_name',   # display only
            'dependent_name',  # display only
            'message_type',    # input from user or device
            'message_type_display',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'guardian_name',
            'dependent_name',
            'message_type_display',
            'created_at',
        ]
    
    def create(self, validated_data):
        guardian = self.context['request'].user.guardian
        if not guardian:
            raise serializers.ValidationError({'detail': _('Guardian profile not found.')})
        
        dependent_id = validated_data.pop('dependent').id
        message_type = validated_data.pop('message_type')
        dependent = guardian.dependents.filter(id=dependent_id).first()
        if not dependent:
            raise serializers.ValidationError({'detail': _('Dependent not found for this guardian.')})
        
        return Message.objects.create(
            guardian=guardian,
            dependent=dependent,
            message_type=message_type,
            **validated_data
        )
    
    