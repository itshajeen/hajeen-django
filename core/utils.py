
import requests
from django.conf import settings 
from fcm_django.models import FCMDevice
from core.models import Notification
from firebase_admin.messaging import Message as FCMMessage, Notification as FCM_Notification

from message.models import Message


TAQNYAT_API_URL = "https://api.taqnyat.sa/v1/messages"
API_KEY = settings.TAQNYAT_API_KEY 

def send_sms(recipients, body, sender, scheduled_datetime=None):
    """
    Send an SMS message via Taqnyat API.
    
    :param recipients: List of phone numbers (list of strings)
    :param body: Message text (string)
    :param sender: Approved sender name (string)
    :param scheduled_datetime: Scheduled send datetime as ISO 8601 string (optional)
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
    if scheduled_datetime:
        payload["scheduledDatetime"] = scheduled_datetime 

    response = requests.post(TAQNYAT_API_URL, headers=headers, json=payload)
    try:
        return response.json()
    except Exception:
        return {"success": False, "message": "Invalid Response from API"}


# # Create Notification 
# def create_notification(user, title, message, notification_type="general"):
#     notification = Notification.objects.create(
#         user=user,
#         title=title,
#         message=message,
#         notification_type=notification_type
#     )
#     return notification


# def send_notification_to_user(user, title, message, data=None):
#     notification_type = data.get("type") if data else "general"
#     notification = create_notification(user, title, message, notification_type=notification_type)

#     devices = FCMDevice.objects.filter(user=user)
#     if devices.exists():
#         safe_data = {str(k): str(v) for k, v in (data or {}).items()}
#         safe_data["notification_id"] = str(notification.id)

#         for device in devices:
#             device.send_message(
#                 message=FCMMessage(
#                     notification=FCM_Notification(title=title, body=message),
#                     data=safe_data
#                 )
#             )
#     return notification


def create_and_send_notification(user, title, message, data_message, notification_type, data_id):
    """
    Create and send a notification to the specified user.
    """
    order = None
    if data_id:
        try:
            dependent_msg = Message.objects.get(id=data_id)
        except Message.DoesNotExist:
            pass  

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        read=False,
        message=message,
        dependent_msg=dependent_msg if data_id else None, 
        title=title
    )

    # Send the notification if the user has registered devices
    devices = FCMDevice.objects.filter(user=user)
    if devices.exists():
        # Ensure all keys and values in data_message are strings
        safe_data_message = {str(k): str(v) for k, v in data_message.items()}
        safe_data_message["notification_id"] = str(notification.id)
        
        devices.send_message(
            Message(
                notification=FCM_Notification(
                    title=title,
                    body=message,
                ),
                data=safe_data_message
            )
        )

    return notification


def send_notification_to_user(user, title, body, data=None):
    """
    Send notification to a user
    
    Args:
        user: User model instance
        title: Notification title
        body: Notification body
        data: Additional data payload
    """
    # Create data message dictionary
    data_message = data or {}
    
    # Get the order ID from data if it exists
    data_id = data.get("message_id") if data else None
    
    # Set notification type based on data
    notification_type = data.get("type", "general") if data else "general"
    
    # Send notification
    return create_and_send_notification(
        user=user,
        title=title,
        message=body,
        data_message=data_message,
        notification_type=notification_type,
        data_id=data_id
    )