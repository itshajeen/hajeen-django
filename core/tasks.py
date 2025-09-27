from django.utils import timezone
from django.db.models import F
from core.utils import send_notification_to_user  
from .utils import send_notification_to_user
from .models import GuardianMessageDefault


# Notify guardians whose message package has expired 
def notify_expired_guardians():
    expired = GuardianMessageDefault.objects.filter(
        messages_per_month__gte=F("app_settings__max_sms_message"),
        notified_expired=False
    )
    for record in expired:
        guardian = record.guardian
        print(f"Notify guardian {guardian.id}: package expired")
        title = "انتهت الباقة الشهرية"
        notification_body = "لقد استهلكت كل الرسائل المسموح بها لهذا الشهر."
        send_notification_to_user(
            user=guardian.user,
            title=title,
            body=notification_body,
            data={"type": "package_expired"}
        )
        record.notified_expired = True
        record.save()


# Reset monthly messages for all guardians at the start of a new month 
def reset_monthly_messages():
    today = timezone.now().date()

    # If it's not the first day of the month, do nothing
    if today.day != 1:
        return  

    records = GuardianMessageDefault.objects.all()
    for record in records:
        record.messages_per_month = record.app_settings.max_sms_message
        record.notified_expired = False
        record.save()

        guardian = record.guardian
        title = "تم تجديد الباقة الشهرية"
        notification_body = f"تم تجديد رصيد رسائلك إلى {record.app_settings.max_sms_message} رسالة."

        send_notification_to_user(
            user=guardian.user,
            title=title,
            body=notification_body,
            data={"type": "package_renewed"}
        )
