import uuid
import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from requests.exceptions import RequestException


class RazorPayManager:
    def __init__(self, request):
        self.key_id = settings.RAZORPAY_API_KEY_ID
        self.key_secret = settings.RAZORPAY_API_KEY_SECRET
        self.url = settings.RAZORPAY_API_URL
        self.request = request

    def create_link(self):
        """Creates a Razorpay payment link and returns the short URL"""

        try:
            amount = Decimal(self.request.data.get('amount', 0))
            if amount <= 0:
                return {"error": "Invalid amount. Amount should be greater than zero."}
        except (InvalidOperation, TypeError):
            return {"error": "Invalid amount format. Please provide a valid number."}

        amount_in_paise = int(round(amount * 100))  # Convert INR to paise
        transaction_id = str(uuid.uuid4())

        data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "reference_id": transaction_id,
            "notes": {
                "amount": str(amount),
                "user": str(self.request.user.id),
                "transaction_id": transaction_id
            }
        }

        try:
            response = requests.post(
                url=self.url,
                auth=(self.key_id, self.key_secret),
                json=data,
                timeout=10
            )
            response.raise_for_status()

            response_data = response.json()
            return response_data.get("short_url", {"error": "Failed to generate payment link"})

        except RequestException as e:
            return {"error": f"Failed to connect to Razorpay: {str(e)}"}

        except ValueError:
            return {"error": "Invalid response from Razorpay"}
