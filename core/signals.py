from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GuardianMessageDefault, AppSettings, Guardian


@receiver(post_save, sender=Guardian)
def create_guardian_message_default(sender, instance, created, **kwargs):
    if not created:
        return

    app_settings = AppSettings.objects.order_by("-id").first()
    if not app_settings:
        return

    GuardianMessageDefault.objects.get_or_create(
        guardian=instance,
        defaults={
            "messages_per_month": app_settings.max_sms_message,
            "app_settings": app_settings,
        },
    )
