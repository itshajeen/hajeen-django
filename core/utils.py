
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

