import requests
from django.conf import settings
from decouple import config

class PaymobService:
    """
    Service class for interacting with Paymob's API.
    """
    BASE_URL = config('PAYMOB_BASE_URL')

    @staticmethod
    def get_auth_token():
        """
        Retrieve the authentication token from Paymob.
        """
        url = f"{PaymobService.BASE_URL}/auth/tokens"
        api_key = config('PAYMOB_API_KEY')
        response = requests.post(url, json={"api_key": api_key})
        if response.status_code != 201:
            raise Exception(f"Failed to get auth token: {response.text}")
        data = response.json()
        token = data.get('token')
        if not token:
            raise Exception("No token returned from Paymob.")
        return token

    @staticmethod
    def create_order(token, currency, amount_cents, items, delivery):
        """
        Create an order in Paymob linked to a Django order.
        """
        url = f"{PaymobService.BASE_URL}/ecommerce/orders"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "currency": currency,
            "amount_cents": amount_cents,
            "items": items,
            "delivery_needed": str(delivery).lower(),
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 201:
            raise Exception(f"Failed to create Paymob order: {response.text}")
        return response.json()

    @staticmethod
    def generate_payment_key(token, currency, expiration, amount_cents, order_id, billing_data):
        """
        Generate a payment key for the Paymob order.
        """
        url = f"{PaymobService.BASE_URL}/acceptance/payment_keys"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "amount_cents": amount_cents,
            "expiration": expiration,
            "order_id": order_id,
            "billing_data": billing_data,
            "currency": currency,
            "integration_id": config('PAYMOB_INTEGRATION_ID')
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 201:
            raise Exception(f"Failed to generate payment key: {response.text}")
        resp_json = response.json()
        payment_key = resp_json.get('token')
        if not payment_key:
            raise Exception("No payment key returned from Paymob.")
        return payment_key

    @staticmethod
    def get_payment_url(payment_key, iframe_id):
        """
        Generate the payment iframe URL.
        """
        return f"{PaymobService.BASE_URL}/acceptance/iframes/{iframe_id}?payment_token={payment_key}" 


