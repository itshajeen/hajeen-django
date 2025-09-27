from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import GuardianMessageDefault, AppSettings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_guardian_message_default(sender, instance, created, **kwargs):
    if created:
        try:
            app_settings = AppSettings.objects.latest("id")
        except AppSettings.DoesNotExist:
            app_settings = None

        if app_settings:
            GuardianMessageDefault.objects.create(
                guardian=instance,
                messages_per_month=app_settings.max_sms_message,
                app_settings=app_settings
            )

