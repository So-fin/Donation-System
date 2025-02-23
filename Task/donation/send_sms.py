import requests
from django.conf import settings

FAST2SMS_API_KEY = settings.FAST2SMS_API_KEY
FAST2SMS_API_URL = settings.FAST2SMS_API_URL

def send_sms(phone_number, message):
    """Send an SMS using Fast2SMS API."""

    if not phone_number or not message:
        return {"error": "Phone number and message required."}

    url = FAST2SMS_API_URL
    payload = {
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": phone_number
    }
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response_data = response.json()

        if response.status_code != 200:
            return {
                "error": f"API request failed with status {response.status_code}",
                "details": response_data
            }

        return {
            "success": True,
            "message": "SMS sent successfully",
            "response": response_data
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}

    except ValueError:
        return {"error": "Invalid response from Fast2SMS API"}
