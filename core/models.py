from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from message.models import Message
from multiselectfield import MultiSelectField


# manager for the User model
class userManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and return a regular user."""
        if not phone_number:
            raise ValueError(_('The phone number field must be set'))
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user 

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Create and return a superuser with admin rights."""
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)  
        return self.create_user(phone_number, password, **extra_fields)


# Phone Regex 
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$', 
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

# User model
class User(AbstractBaseUser, PermissionsMixin):
    # User Roles 
    ROLES_CHOICES = (
        ('admin', _('Admin')),
        ('guardian', _('Guardian')),
        ('dependent', _('Dependent')),
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)  # max_length 17 for country code and number
    role = models.CharField(max_length=50, choices=ROLES_CHOICES)
    otp = models.CharField(max_length=6, null=True, blank=True)  # OTP for verification
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True) 
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  
    is_admin = models.BooleanField(default=False)
    is_block = models.BooleanField(default=False) # Field to block the user 
    is_deleted = models.BooleanField(default=False) # Soft delete field 
    objects = userManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    @property
    def is_follower(self):
        return self.role == 'follower'

    class Meta:
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.phone_number 


# Guardian model
class Guardian(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guardian')
    guardian_code_hashed = models.CharField(max_length=255, null=True, blank=True)
    pin_reset_otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Set the guardian code with hashing 
    def set_code(self, raw_code):
        self.guardian_code_hashed = make_password(raw_code)
        self.save()

    # Check the guardian code against the hashed version 
    def check_code(self, raw_code):
        return check_password(raw_code, self.guardian_code_hashed)

    def __str__(self):
        return self.user.phone_number
    

# Disablity model
class DisabilityType(models.Model):
    name_ar = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[('active', _('Active')), ('inactive', _('Inactive'))], default='active')
    created_at = models.DateTimeField(auto_now_add=True) 
    def __str__(self):
        return self.name_en or self.name_ar 
    

# Dependent Model 
class Dependent(models.Model):
    # Control Method Choices
    CONTROL_METHOD_CHOICES = (
        ('eye', _('Eye Only')),
        ('eye_lip', _('Eye and Lips')),
    )

    # Degree Type Choices 
    DEGREE_TYPE_CHOICES = (
        ('higher', _('Higher Education')),
        ('general', _('General Education')),
        ('other', _('Other')),
    )

    # Field of Interest Choices 
    INTEREST_FIELD_CHOICES = (
        ('tech', _('Tech, Cybersecurity, and AI')),
        ('design', _('Design, Graphics, and UX')),
        ('business', _('Business, Entrepreneurship, and Marketing')),
        ('medical', _('Medicine and Health')),
        ('law', _('Law and Regulations')),
        ('education', _('Education, Training, and Mentoring')),
        ('engineering', _('Engineering (All Types)')),
        ('science', _('Natural Sciences (Physics, Chemistry, Biology)')),
        ('earth', _('Earth and Environmental Sciences')),
        ('languages', _('Languages and Literature')),
    )

    # Dependent model fields 
    name = models.CharField(max_length=255) 
    guardian = models.ForeignKey(Guardian, related_name='dependents', on_delete=models.CASCADE) 
    date_birth = models.DateField(null=True, blank=True)
    control_method = models.CharField(max_length=20, choices=CONTROL_METHOD_CHOICES) # No Default 
    disability_type = models.ForeignKey(DisabilityType, related_name='dependents', on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=[('male', _('Male')), ('female', _('Female'))])
    marital_status = models.CharField(max_length=20, choices=[('single', _('Single')), ('married', _('Married'))], default='single')
    degree_type = models.CharField(
        max_length=100,
        choices=DEGREE_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name=_('Degree Type')
    )
    degree_type_other = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Custom Degree Type'),
        help_text=_('Custom degree type when "other" is selected')
    )
    
    interest_field = MultiSelectField(
        choices=INTEREST_FIELD_CHOICES,
        null=True,
        blank=True,
        verbose_name=_('Field of Interest')
    )
    # Device Registration ID for Push Notifications 
    registration_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        unique=True, 
        verbose_name=_("Device Registration ID")
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


# App Settings 
class AppSettings(models.Model):
    version = models.CharField(max_length=10, verbose_name=_("App Version"))
    whatsapp_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)  # max_length 17 for country code and number
    max_sms_message = models.IntegerField(default=1, verbose_name=_("Max SMS Messages"))
    pending_guardian_increment = models.IntegerField(
        default=0,
        verbose_name=_("Pending Guardian Increment"),
        help_text=_("Number of additional messages to add to guardians with expired packages when they renew."))


# Notification Model 
class Notification(models.Model):
    TYPES = (
        ('general', _('General')),
        ('new_message', _('New Message')),
        ('package_expired', _('Package Expired')),
        ('package_renewed', _('Package Renewed')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    dependent_msg = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(_("message"), max_length=1024)
    notification_type = models.CharField(_('type'), max_length=100, choices=TYPES, null=True, blank=True)
    title = models.CharField(_("title"), max_length=255, null=True, blank=True)
    read = models.BooleanField(_('read'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def _str_(self):
        return f"{self.get_notification_type_display()} - {self.user}"


# Guardian Message Default 
class GuardianMessageDefault(models.Model):
    guardian = models.OneToOneField(
        "Guardian",
        on_delete=models.CASCADE,
        related_name="message_defaults"
    )
    messages_per_month = models.PositiveIntegerField(default=0)
    app_settings = models.ForeignKey(
        AppSettings,
        on_delete=models.CASCADE,
        related_name="guardian_defaults"
    )
    notified_expired = models.BooleanField(default=False)  # To track if the guardian has been notified about expiration
    def is_package_expired(self):
        return self.messages_per_month >= self.app_settings.max_sms_message

    def __str__(self):
        return f"{self.guardian} - {self.messages_per_month} msgs (v{self.app_settings.version})"
