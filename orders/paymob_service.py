import requests
from django.conf import settings
from paymob.accept import AcceptAPIClient

accept_client = AcceptAPIClient()


def create_paymob_order(order):
    url = "https://accept.paymob.com/api/ecommerce/orders"
    headers = {"Authorization": f"Bearer {settings.PAYMOB_API_KEY}"}
    data = {
        "merchant_order_id": str(order.id),
        "amount_cents": int(order.total_amount * 100),
        "currency": "EGP",
        "delivery_needed": "false"
    }
    response = requests.post(url, json=data, headers=headers)
    response_data = response.json()
    order.paymob_order_id = response_data['id']
    order.save()
    return response_data['id']


def get_payment_key(paymob_order_id, order, billing_data=None):
    url = "https://accept.paymob.com/api/acceptance/payment_keys"
    headers = {"Authorization": f"Bearer {settings.PAYMOB_API_KEY}"}
    if billing_data is None:
        billing_data = {
            "email": order.user.email if hasattr(order.user, 'email') else "user@example.com",
            "first_name": getattr(order.user, 'first_name', 'John'),
            "last_name": getattr(order.user, 'last_name', 'Doe'),
            "phone_number": getattr(order.user, 'phone', '+201234567890'),
        }
    data = {
        "order_id": paymob_order_id,
        "billing_data": billing_data,
        "amount_cents": str(int(order.total_amount * 100)),
        "currency": "EGP"
    }
    response = requests.post(url, json=data, headers=headers)
    response_data = response.json()
    return response_data['token']


def verify_transaction(transaction_id):
    code, transaction, feedback = accept_client.get_transaction(transaction_id)
    return code == 10 and transaction.success 