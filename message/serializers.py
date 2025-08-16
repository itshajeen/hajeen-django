from rest_framework import serializers 
from django.utils.translation import gettext_lazy as _
from .models import GuardianMessageType, MessageType, Message 


# MessageType Serializer 
class MessageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageType
        fields = ['id', 'label_ar', 'label_en', 'audio_file_ar', 'audio_file_en', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_status(self, value):
        if value not in ['active', 'inactive']:
            raise serializers.ValidationError({"detail" : _('Invalid status.')})
        return value        


# GuardianMessageType Serializer 
class GuardianMessageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardianMessageType 
        fields = ['id', 'guardian', 'message_type'] 
        read_only_fields = ['id', 'guardian']

        def create(self, validated_data):
            guardian = self.context['request'].user.guardian
            if not guardian:
                raise serializers.ValidationError({'detail': _('Guardian profile not found.')})
            
            message_type = validated_data.pop('message_type')
            return GuardianMessageType.objects.get_or_create(guardian=guardian, message_type=message_type)

    def validate_message_type(self, value):
        if not MessageType.objects.filter(id=value.id).exists():
            raise serializers.ValidationError({'detail': _('Invalid message type.')})
        return value
    

    def to_representation(self, instance):
        response =  super().to_representation(instance)
        response['message_type'] = MessageTypeSerializer(instance.message_type).data 
        return response 



# For bulk create
class GuardianMessageTypeSerializer(serializers.ModelSerializer):
    message_type = MessageTypeSerializer(read_only=True)

    class Meta:
        model = GuardianMessageType
        fields = ['id', 'guardian', 'message_type']
        read_only_fields = ['id', 'guardian']


# GuardianMessageType Bulk Create Serializer 
class GuardianMessageTypeBulkUpsertSerializer(serializers.Serializer):
    message_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate_message_type_ids(self, value):
        existing_ids = set(MessageType.objects.filter(id__in=value).values_list('id', flat=True))
        missing = set(value) - existing_ids
        if missing:
            raise serializers.ValidationError({"detail": f"Message types not found: {list(missing)}"})
        return value

    def create(self, validated_data):
        guardian = self.context['request'].user.guardian
        if not guardian:
            raise serializers.ValidationError({'detail': _('Guardian profile not found.')})

        new_ids = set(validated_data['message_type_ids'])
        old_ids = set(guardian.guardian_messages.values_list('message_type_id', flat=True))

        GuardianMessageType.objects.filter(
            guardian=guardian,
            message_type_id__in=(old_ids - new_ids)
        ).delete()

        created_objects = []
        for mt_id in (new_ids - old_ids):
            obj = GuardianMessageType.objects.create(
                guardian=guardian,
                message_type_id=mt_id
            )
            created_objects.append(obj)

        updated_qs = GuardianMessageType.objects.filter(guardian=guardian)
        return updated_qs

    def to_representation(self, instances):
        return [
            {
                "id": instance.id,
                "guardian": instance.guardian.id,
                "message_type": MessageTypeSerializer(instance.message_type).data
            }
            for instance in instances
        ]



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
    
    def validate_message_type(self, value):
        if not MessageType.objects.filter(id=value.id).exists():
            raise serializers.ValidationError({'detail': _('Invalid message type.')}) 
        return value
    
    