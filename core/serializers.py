from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import  Follower, User, Patient
import random


# Phone Login Serializer 
class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'role': 'patient', 'is_active': True, 'is_block': False}
        )
    
        if created and user.role == 'patient':
            Patient.objects.create(user=user)

        # Check if user is blocked 
        if user.is_block :
            raise serializers.ValidationError({"detail": _('User account is blocked.')}) 
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.save()

        # TODO: Send OTP via SMS (Twilio, etc.)
        print(f"OTP for {user.phone_number} is {otp}")

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
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'role', 'profile_picture'] 
        read_only_fields = ['role']  # Read-only fields for the get endpoint

    # Get Profile Picture 
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None


# User Profile Update Serializer 
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'role', 'profile_picture']  # Define fields to update
        extra_kwargs = {
            'role': {'read_only': True}           # Prevent updating role
        }



# Follower Serializer for updating Follower and User data 
class FollowerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_picture = serializers.ImageField(source='user.profile_picture', required=False)
    is_active = serializers.BooleanField(required=False)
    is_block = serializers.BooleanField(required=False)

    class Meta:
        model = Follower
        fields = [
            'id',
            'name',
            'phone_number',
            'profile_picture',
            'is_active',
            'is_block',
            'description',
            'location',
            'created_at',
        ]

    def update(self, instance, validated_data):
        user = instance.user

        # Check if the phone number is provided and validate it 
        new_phone = validated_data.get('phone_number')
        if new_phone and new_phone != user.phone_number:
            if user.__class__.objects.filter(phone_number=new_phone).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({'detail': _('Phone number already exists.')})
            user.phone_number = new_phone

        user.name = validated_data.get('name', user.name)
        user.is_active = validated_data.get('is_active', user.is_active)
        user.is_block = validated_data.get('is_block', user.is_block)

        if 'profile_picture' in validated_data:
            user.profile_picture = validated_data['profile_picture']

        user.save()

        # Update Follower fields 
        instance.save()

        return instance

    def create(self, validated_data):
        # Extract user-related fields
        user_data = {
            'name': validated_data.pop('name', ''),
            'phone_number': validated_data.pop('phone_number', ''),
            'profile_picture': validated_data.pop('profile_picture', None),
            'is_active': validated_data.pop('is_active', True),
            'is_block': validated_data.pop('is_block', False),
            'role': 'follower'
        }

        # Check if phone number already exists
        if User.objects.filter(phone_number=user_data['phone_number']).exists():
            raise serializers.ValidationError({'detail': _('Phone number already exists.')})

        user = User.objects.create(**user_data)
        follower = Follower.objects.create(user=user, **validated_data)
        return follower 
