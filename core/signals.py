from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GuardianMessageDefault, AppSettings, Guardian


@receiver(post_save, sender=Guardian)
def create_guardian_message_default(sender, instance, created, **kwargs):
    # Defensive: this signal must only ever run for Guardian instances.
    # (If it gets connected incorrectly in another environment, bail out.)
    # Multiple checks to ensure we only process Guardian instances
    
    # Check sender first
    if sender != Guardian:
        return
    
    # Check instance type using multiple methods
    if not isinstance(instance, Guardian):
        return
    
    # Check if instance has Guardian-specific attributes
    if not hasattr(instance, 'user') or not hasattr(instance, 'guardian_code_hashed'):
        return
    
    # Additional check: verify the instance's model is Guardian using _meta
    try:
        if instance._meta.model_name != 'guardian' or instance._meta.label != 'core.Guardian':
            return
    except (AttributeError, Exception):
        # If _meta check fails, fall back to class check
        if instance.__class__ != Guardian:
            return
    
    if not created:
        return
        
    try:
        app_settings = AppSettings.objects.latest("id")
    except AppSettings.DoesNotExist:
        app_settings = None

    if app_settings:
        # Only create if it doesn't already exist
        # Wrap in try-except as final safety measure
        try:
            GuardianMessageDefault.objects.get_or_create(
                guardian=instance,
                defaults={
                    'messages_per_month': app_settings.max_sms_message,
                    'app_settings': app_settings
                }
            )
        except (ValueError, TypeError) as e:
            # If somehow a non-Guardian instance got through, log and ignore
            # This should never happen with all the checks above, but just in case
            return

