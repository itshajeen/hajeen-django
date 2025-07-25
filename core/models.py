from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


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


# User model
class User(AbstractBaseUser, PermissionsMixin):
    # Phone Regex 
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    # User Roles 
    ROLES_CHOICES = (
        ('admin', _('Admin')),
        ('follower', _('Folower')),
        ('patient', _('Patient')),
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)  # max_length 17 for country code and number
    role = models.CharField(max_length=50, choices=ROLES_CHOICES)
    otp = models.CharField(max_length=6, null=True, blank=True)  # OTP for verification
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  
    is_admin = models.BooleanField(default=False)
    is_block = models.BooleanField(default=False) # Field to block the user 
    objects = userManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []


    @property
    def is_client(self):
        return self.role == 'client'

    @property
    def is_craftsman(self):
        return self.role == 'craftsman'

    class Meta:
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.phone_number 


# Craftsman model
class Follower(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.phone_number
    

# Client model
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.phone_number


