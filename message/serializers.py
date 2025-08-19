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
    class Meta:
        model = Message
        fields = [
            'id', 'guardian', 'dependent', 'message_type', 'created_at', 
            'is_seen', 'is_sms', 'is_voice', 'is_emergency'
        ]
        read_only_fields = ['guardian', 'dependent', 'created_at', 'is_seen']

    def validate(self, attrs):
        # check that message type with is_sms or is_voice 
        if attrs.get('is_sms') and attrs.get('is_voice'):
            raise serializers.ValidationError(
                {"detail": _('A message cannot be both SMS and voice.')}
            )

        # check that is_emergency 
        is_emergency = attrs.get('is_emergency', False)
        message_type = attrs.get('message_type', None)

        if is_emergency and message_type is not None:
            raise serializers.ValidationError(
                {"detail": _('Emergency messages should not have a message type.')}
            )
        if not is_emergency and message_type is None:
            raise serializers.ValidationError(
                {"detail": _('Non-emergency messages must have a message type.')}
            )

        return attrs

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.message_type:
            response['message_type'] = GuardianMessageTypeSerializer(instance.message_type).data
        else:
            response['message_type'] = None
        return response
    

# Mini Serializer for Message 
class MessageMiniSerializer(serializers.ModelSerializer):
    message_type = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        model = Message
        fields = ['id', 'message_type', 'created_at', 'is_seen']

    def get_message_type(self, obj):
        if obj.message_type and obj.message_type.message_type:
            return obj.message_type.message_type.label_ar
        return None
