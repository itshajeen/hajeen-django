
import requests
from django.conf import settings 

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

# utils/notifications.py

from fcm_django.models import FCMDevice
from core.models import Notification

def create_notification(user, title, message, notification_type="general"):
    """
    إنشاء Notification object في قاعدة البيانات.
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )
    return notification



# Send Fcm Notification 
def send_fcm_notification(user, title, message, data=None):
    devices = FCMDevice.objects.filter(user=user)
    if not devices.exists():
        return None

    safe_data = {str(k): str(v) for k, v in (data or {}).items()}
    if "notification_id" not in safe_data:
        notification = create_notification(user, title, message, notification_type=safe_data.get("type", "general"))
        safe_data["notification_id"] = str(notification.id)
    else:
        notification = None  

    devices.send_message(
        title=title,
        body=message,
        data=safe_data
    )
    return notification


def send_notification_to_user(user, title, message, data=None):
    notification_type = (data.get("type") if data else "general")
    
    notification = create_notification(user, title, message, notification_type=notification_type)

    devices = FCMDevice.objects.filter(user=user)
    if devices.exists():
        safe_data = {str(k): str(v) for k, v in (data or {}).items()}
        safe_data["notification_id"] = str(notification.id)

        devices.send_message(
            title=title,
            body=message,
            data=safe_data
        )

    return notification
