
import requests
from django.conf import settings 
from fcm_django.models import FCMDevice
from core.models import Notification
from firebase_admin.messaging import Message as FCMMessage, Notification as FCM_Notification


TAQNYAT_API_URL = "https://api.taqnyat.sa/v1/messages"
API_KEY = settings.TAQNYAT_API_KEY 


def send_sms(recipients, body, sender, scheduled=None):
    """
    Send an SMS message via Taqnyat API.
    
    :param recipients: List of phone numbers (list of strings)
    :param body: Message text (string)
    :param sender: Approved sender name (string)
    :param scheduled: Scheduled send datetime as ISO 8601 string (optional)
    :return: API response (dict)
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "recipients": recipients,
        "body": body,
        "sender": sender
    }
    if scheduled:
        payload["scheduled"] = scheduled

    response = requests.post(TAQNYAT_API_URL, headers=headers, json=payload)
    try:
        return response.json()
    except Exception:
        return {"success": False, "message": "Invalid Response from API"}



# Create Notification 
def create_notification(user, title, message, notification_type="general"):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )
    return notification


def send_notification_to_user(user, title, message, data=None):
    notification_type = data.get("type") if data else "general"
    notification = create_notification(user, title, message, notification_type=notification_type)

    devices = FCMDevice.objects.filter(user=user)
    if devices.exists():
        safe_data = {str(k): str(v) for k, v in (data or {}).items()}
        safe_data["notification_id"] = str(notification.id)

        for device in devices:
            device.send_message(
                message=FCMMessage(
                    notification=FCM_Notification(title=title, body=message),
                    data=safe_data
                )
            )
    return notification
