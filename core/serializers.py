from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.utils import timezone 
from rest_framework import serializers

from message.serializers import MessageMiniSerializer
from django.conf import settings
from .models import  AppSettings, DisabilityType, Guardian, Dependent, GuardianMessageDefault, User 
from .utils import TaqnyatSMSService 
import random

# Phone Login Serializer 
class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'role': 'guardian', 'is_active': True, 'is_block': False}
        )
    
        if created and user.role == 'guardian':
            Guardian.objects.create(user=user)

        # Check if user is blocked 
        if user.is_block :
            raise serializers.ValidationError({"detail": _('تم حظر حساب المستخدم.')}) 
        
        if user.is_deleted:
            raise serializers.ValidationError({"detail": _('تم حذف حساب المستخدم. يرجى الاتصال بالدعم الفني.')})
        
        # OTP ثابت لرقم معين
        if phone_number == "507177774":  
            otp = "2252"
        else:
            otp = str(random.randint(1000, 9999))

        user.otp = otp
        user.save()
        print(f"OTP for {user.phone_number} is {otp}")

        # Send OTP via SMS
        sms_service = TaqnyatSMSService()
        sms_response = sms_service.send_sms(
            recipients=[user.phone_number],
            message=f"عزيزنا العميل،\nكود التحقق الخاص بكم للدخول الى منصة شركة رزان عدنان المليك للتجارة هو {otp}",
            sender_name=settings.TAQNYAT_SENDER_NAME
        )
        print(f"SMS Response: {sms_response}")

        attrs['user'] = user
        return attrs


# Phone Password Login Serializer
class PhonePasswordLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if not user:
            raise serializers.ValidationError({"detail" : _('Invalid phone number or password.')})

        if not user.is_active:
            raise serializers.ValidationError({"detail" : _('User account is disabled.')})

        attrs['user'] = user
        return attrs


# User Serializer 
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'phone_number', 'role', 'profile_picture', 'is_block']  # Include all fields
        read_only_fields = ['id', 'role']  # Read-only fields for the get endpoint
        extra_kwargs = {
            'is_block': {'required': False},
        }


# User Profile Serializer 
class UserProfileSerializer(serializers.ModelSerializer):
    dependents_count = serializers.SerializerMethodField(read_only=True)
    has_guardian_code = serializers.SerializerMethodField(read_only=True)
    messages_count = serializers.SerializerMethodField(read_only=True) 
    remaining_sms = serializers.SerializerMethodField(read_only=True) 

    class Meta:
        model = User
        fields = ['name', 'phone_number', 'role', 'profile_picture', 'address', 'dependents_count', 'has_guardian_code', 'messages_count', 'remaining_sms'] 
        read_only_fields = ['role']  # Read-only fields for the get endpoint

    # Get Dependents Count 
    def get_dependents_count(self, obj):
        if obj.role == 'guardian' and hasattr(obj, 'guardian'):
            return obj.guardian.dependents.count()
        return 0
    
    # Get Messages Count
    def get_messages_count(self, obj):
        if obj.role == 'guardian' and hasattr(obj, 'guardian'):
            return obj.guardian.received_messages.count()
        return 0

    # Get Profile Picture 
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None
    
    # Check if Guardian has PIN Code 
    def get_has_guardian_code(self, obj):
        if obj.role == 'guardian' and hasattr(obj, 'guardian'):
            return bool(obj.guardian.guardian_code_hashed)
        return False

    # Get Remaining SMS Count 
    def get_remaining_sms(self, obj):
        if obj.role != 'guardian' or not hasattr(obj, 'guardian'):
            return None
        from core.models import GuardianMessageDefault  # import inside to avoid circular imports
        try:
            guardian_defaults = obj.guardian.message_defaults
            return max(guardian_defaults.messages_per_month, 0)
        except GuardianMessageDefault.DoesNotExist:
            return 0



# User Profile Update Serializer 
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'role', 'profile_picture', 'address']  # Define fields to update
        read_only_fields = ['role', 'phone_number']


# Set Guardian PIN Code Serializer 
class SetGuardianPinCodeSerializer(serializers.Serializer):
    pin_code = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if user.role != 'guardian':
            raise serializers.ValidationError({"detail" : _("Only guardians can set PIN code.")})

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            raise serializers.ValidationError({"detail" : _("Guardian not found.")})

        if guardian.guardian_code_hashed:
            raise serializers.ValidationError({"detail" : _("PIN code already set. You can reset it.")})

        attrs['guardian'] = guardian
        return attrs

    def create(self, validated_data):
        guardian = validated_data['guardian']
        guardian.set_code(validated_data['pin_code'])
        return guardian


# Guardian Serializer 
class GuardianSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_picture = serializers.ImageField(source='user.profile_picture', required=False)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    is_block = serializers.BooleanField(source='user.is_block', required=False)
    is_deleted = serializers.BooleanField(source='user.is_deleted', required=False) 
    dependents = serializers.SerializerMethodField()
    message_limit = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            'id',
            'name',
            'phone_number',
            'profile_picture',
            'is_active',
            'is_block',
            'is_deleted',
            'dependents',
            'created_at',
            'message_limit'
        ]

    # Get Dependents 
    def get_dependents(self, obj):
        dependents = obj.dependents.all()
        return DependentSerializer(dependents, many=True, context=self.context).data

    # Get Message Limit 
    def get_message_limit(self, obj):
        if hasattr(obj, "message_defaults"):
            return obj.message_defaults.messages_per_month
        return 0

    # Create or Update Guardian 
    def create(self, validated_data):
        # Extract user data from validated_data 
        user_data = validated_data.pop('user', {})

        # Check if phone number is provided and unique 
        phone_number = user_data.get('phone_number')
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({'detail': _('Phone number already exists.')})

        # Create the User instance 
        user = User.objects.create(
            name=user_data.get('name', ''),
            phone_number=phone_number,
            profile_picture=user_data.get('profile_picture', None),
            is_active=user_data.get('is_active', True),
            is_block=user_data.get('is_block', False),
            role='guardian',
        )

        # Create the Guardian instance 
        guardian = Guardian.objects.create(user=user, **validated_data)
        return guardian

    def update(self, instance, validated_data):
        user = instance.user
        user_data = validated_data.pop('user', {})

        # Check if phone number is provided and unique 
        new_phone = user_data.get('phone_number')
        if new_phone and new_phone != user.phone_number:
            if User.objects.filter(phone_number=new_phone).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({'detail': _('Phone number already exists.')})
            user.phone_number = new_phone

        # Update user fields 
        user.name = user_data.get('name', user.name)
        user.is_active = user_data.get('is_active', user.is_active)
        user.is_block = user_data.get('is_block', user.is_block)

        if 'profile_picture' in user_data:
            user.profile_picture = user_data['profile_picture']

        user.save()
        instance.save()

        return instance

# Simple Guardian Serializer for listing
class SimpleGuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = ['id', 'user']  # Include only necessary fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user, context=self.context).data
        return representation
    

# Disability Type Serializer 
class DisabilityTypeSerializer(serializers.ModelSerializer):
    dependents_count = serializers.SerializerMethodField()

    class Meta:
        model = DisabilityType 
        fields = ['id', 'name_en', 'name_ar', 'status', 'created_at', 'dependents_count']
        read_only_fields = ['created_at']
        extra_kwargs = {
            'status': {'required': False},
        }

    def get_dependents_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_staff:
            return obj.dependents.count()
        return None  # Only return count if user is staff 

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if not request or not request.user.is_staff:
            representation.pop('dependents_count', None)
        return representation


# Dependent Serializer 
class DependentSerializer(serializers.ModelSerializer):
    guardian = SimpleGuardianSerializer(read_only=True)
    interest_field = serializers.ListField(
        child=serializers.ChoiceField(choices=Dependent.INTEREST_FIELD_CHOICES),
        required=False
    )
    # last messages for the dependent 
    last_messages = serializers.SerializerMethodField(read_only=True)  
    last_activity = serializers.SerializerMethodField(read_only=True)  
    total_messages = serializers.SerializerMethodField(read_only=True)  
    sms_messages = serializers.SerializerMethodField(read_only=True)    

    class Meta:
        model = Dependent
        fields = [
            'id', 'name', 'disability_type', 'control_method', 'gender', 'date_birth',
            'guardian', 'created_at', 'degree_type', 'degree_type_other', 'marital_status', 'interest_field', 'last_messages', 'last_activity', 'total_messages', 'sms_messages'
        ]

    def create(self, validated_data):
        guardian = self.context['request'].user.guardian
        if not guardian:
            raise serializers.ValidationError({'detail': _('Guardian profile not found.')})
        return Dependent.objects.create(guardian=guardian, **validated_data)

    def validate(self, attrs):
        # Validate control method
        if attrs['control_method'] not in dict(Dependent.CONTROL_METHOD_CHOICES).keys():
            raise serializers.ValidationError({'control_method': _('Invalid control method.')})
        
        # Validate degree_type_other when degree_type is "other"
        degree_type = attrs.get('degree_type')
        degree_type_other = attrs.get('degree_type_other')
        
        if degree_type == 'other':
            if not degree_type_other or not degree_type_other.strip():
                raise serializers.ValidationError({
                    'degree_type_other': _('Custom degree type is required when "other" is selected.')
                })
        elif degree_type_other:
            # Clear degree_type_other if degree_type is not "other"
            attrs['degree_type_other'] = None
        
        # Validate date of birth
        if 'date_birth' in attrs and attrs['date_birth'] is not None:
            today = timezone.now().date()
            if attrs['date_birth'] > today:
                raise serializers.ValidationError({'date_birth': _('Date of birth must be in the past.')})
            age = today.year - attrs['date_birth'].year - (
                (today.month, today.day) < (attrs['date_birth'].month, attrs['date_birth'].day)
            )
            if age > 200:
                raise serializers.ValidationError({'date_birth': _('Age cannot be more than 200 years.')})
        return attrs


    def get_last_messages(self, obj):
        messages = obj.sent_messages.order_by('-created_at')[:5]  # last five messages
        return MessageMiniSerializer(messages, many=True, context=self.context).data


    def get_last_activity(self, obj):
        last_message = obj.sent_messages.order_by('-created_at').first()
        if last_message:
            return {
                "id": last_message.id,
                "created_at": last_message.created_at,
                "type": last_message.message_type.message_type.label_en if last_message.message_type else None,
            }
        return None

    def get_total_messages(self, obj):
        return obj.sent_messages.count()

    def get_sms_messages(self, obj):
        return obj.sent_messages.filter(is_sms=True).count()


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['guardian'] = SimpleGuardianSerializer(instance.guardian, context=self.context).data
        representation['disability_type'] = DisabilityTypeSerializer(instance.disability_type, context=self.context).data
        return representation


# App Settings Serializer 
class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = '__all__'


# Guardian Message Default Serializer 
class GuardianMessageDefaultSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardianMessageDefault
        fields = ["id", "guardian", "messages_per_month", "app_settings"]
        read_only_fields = ["id", "guardian", "app_settings"]

