
import requests
import logging
from django.conf import settings 
from fcm_django.models import FCMDevice
from core.models import Notification
from firebase_admin.messaging import Message as FCMMessage, Notification as FCM_Notification, AndroidConfig, APNSConfig, APNSPayload, Aps
from message.models import Message


logger = logging.getLogger(__name__)

# Taqnyat SMS Service 
class TaqnyatSMSService:
    def __init__(self):
        self.api_key = settings.TAQNYAT_API_KEY
        self.base_url = settings.TAQNYAT_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def send_sms(self, recipients, message, sender_name="SMS"):
        try:
            # Ensure recipients is a list 
            if isinstance(recipients, str):
                recipients = [recipients]
            
            # Format phone numbers to include country code if missing 
            formatted_recipients = []
            for recipient in recipients:
                if not recipient.startswith('+'):
                    if recipient.startswith('966'):
                        recipient = f'+{recipient}'
                    elif recipient.startswith('05'):
                        recipient = f'+966{recipient[1:]}'
                    else:
                        recipient = f'+966{recipient}'
                formatted_recipients.append(recipient)
            
            payload = {
                'recipients': formatted_recipients,
                'body': message,
                'sender': sender_name
            }
            
            logger.info(f"Sending SMS to {formatted_recipients}: {message}")
            
            response = requests.post(
                f'{self.base_url}/v1/messages',
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200:
                logger.info(f"SMS sent successfully: {response_data}")
                return {
                    'success': True,
                    'message': 'تم إرسال الرسالة بنجاح',
                    'data': response_data,
                    'message_id': response_data.get('messageId'),
                    'cost': response_data.get('cost')
                }
            else:
                logger.error(f"SMS sending failed: {response_data}")
                return {
                    'success': False,
                    'message': 'فشل في إرسال الرسالة',
                    'error': response_data.get('message', 'خطأ غير معروف'),
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                'success': False,
                'message': 'خطأ في الاتصال بخدمة الرسائل',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'message': 'حدث خطأ غير متوقع',
                'error': str(e)
            }
    
    
    def get_message_status(self, message_id):
        try:
            response = requests.get(
                f'{self.base_url}/v1/messages/{message_id}',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                status_data = response.json()
                return {
                    'success': True,
                    'status': status_data.get('status'),
                    'data': status_data
                }
            else:
                return {
                    'success': False,
                    'message': 'فشل في استعلام حالة الرسالة',
                    'error': response.text
                }
                
        except Exception as e:
            logger.error(f"Message status check error: {str(e)}")
            return {
                'success': False,
                'message': 'خطأ في استعلام حالة الرسالة',
                'error': str(e)
            }


# ---------------------------
def create_and_send_notification(user, title, message, data_message, notification_type, data_id):
    """
    Create and send a notification to the specified user.
    If is_voice=True in data_message, notification will include sound.
    """
    # Ensure dependent_msg is always defined
    dependent_msg = None
    if data_id:
        try:
            dependent_msg = Message.objects.get(id=data_id)
        except Message.DoesNotExist:
            pass  

    # Create notification in DB
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        read=False,
        message=message,
        dependent_msg=dependent_msg, 
        title=title
    )

    # Send the notification if the user has registered devices
    devices = FCMDevice.objects.filter(user=user)
    if devices.exists():
        # Ensure all keys and values in data_message are strings
        safe_data_message = {str(k): str(v) for k, v in data_message.items()}
        safe_data_message["notification_id"] = str(notification.id)

        # Decide sound type based on is_voice flag in payload
        sound_type = "default" if safe_data_message.get("is_voice") == "True" else None

        devices.send_message(
            FCMMessage(
                notification=FCM_Notification(
                    title=title,
                    body=message,  # Fixed here
                ),
                android=AndroidConfig(
                    notification={'sound': 'default'}  # Android sound
                ),
                apns=APNSConfig(
                    payload=APNSPayload(aps=Aps(sound='default'))  # iOS sound
                ),
                data=safe_data_message
            )
        )
    else:
        logger.info(f"No FCM devices found for user {user.id}. Notification saved but not sent.")

    return notification


# ---------------------------
# Helper to send notification 
# ---------------------------
def send_notification_to_user(user, title, body, data=None):
    """
    Send notification to a user
    
    Args:
        user: User model instance
        title: Notification title
        body: Notification body
        data: Additional data payload (must include 'is_voice' if needed)
    """
    data_message = data or {}
    data_id = data.get("message_id") if data else None
    notification_type = data.get("type", "general") if data else "general"
    
    return create_and_send_notification(
        user=user,
        title=title,
        message=body,
        data_message=data_message,
        notification_type=notification_type,
        data_id=data_id
    )
