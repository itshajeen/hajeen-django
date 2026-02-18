from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GuardianMessageDefault, AppSettings, Guardian


@receiver(post_save, sender=Guardian)
def create_guardian_message_default(sender, instance, created, **kwargs):
    if created:
        # Defensive: this signal must only ever run for Guardian instances.
        # (If it gets connected incorrectly in another environment, bail out.)
        if sender != Guardian or not isinstance(instance, Guardian):
            return
        try:
            app_settings = AppSettings.objects.latest("id")
        except AppSettings.DoesNotExist:
            app_settings = None

        if app_settings:
            # Only create if it doesn't already exist
            GuardianMessageDefault.objects.get_or_create(
                guardian=instance,
                defaults={
                    'messages_per_month': app_settings.max_sms_message,
                    'app_settings': app_settings
                }
            )

