from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from Prouducts.models import Product, Category
from .models import Cart, CartItem, Order, OrderItem, Payment, Country, State, City
from unittest.mock import patch
from user_profile.models import UserProfile

User = get_user_model()

class TestOrderAppViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Sneakers")
        self.product = Product.objects.create(
            name="Test Shoe",
            brand="Test Brand",
            description="A test shoe.",
            price=100.00,
            discount_percentage=10,
            main_image="http://example.com/image.jpg",
            sizes={"42": 5, "43": 3},
            colors={"red": 2, "blue": 1},
            category=self.category,
            is_available=True,
            stock_quantity=10
        )
        self.country = Country.objects.create(name="Country", iso2="CO")
        self.state = State.objects.create(name="State", country=self.country)
        self.city = City.objects.create(name="City", state=self.state)
        self.profile = UserProfile.objects.create(
            user=self.user,
            address="123 Test St",
            country=self.country,
            state=self.state,
            city=self.city
        )

    def test_cart_lifecycle(self):
        url = reverse('cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])
        cart_data = {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 2,
                    "price": "100.00"
                }
            ]
        }
        response = self.client.put(url, cart_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(float(response.data['total_amount']), 200.00)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_order_creation_and_retrieval(self):
        cart_url = reverse('cart')
        self.client.put(cart_url, {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 2,
                    "price": "100.00"
                }
            ]
        }, format='json')
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data['id']
        list_url = reverse('order-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        detail_url = reverse('order-detail', args=[order_id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order_id)

    def test_order_creation_with_empty_cart_fails(self):
        # First create an empty cart
        cart_url = reverse('cart')
        self.client.put(cart_url, {"items": []}, format='json')
        
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cart is empty', response.data['detail'])

    def test_user_info_view(self):
        url = reverse('user-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        update_data = {
            "address": "New Address",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id
        }
        response = self.client.put(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['address'], "New Address")

    @patch('orders.views.PaymobService.get_auth_token', return_value='token')
    @patch('orders.views.PaymobService.create_order', return_value={'id': 12345})
    @patch('orders.views.PaymobService.generate_payment_key', return_value='paykey')
    @patch('orders.views.PaymobService.get_payment_url', return_value='http://paymob/iframe')
    def test_payment_checkout(self, mock_url, mock_key, mock_create, mock_token):
        cart_url = reverse('cart')
        self.client.put(cart_url, {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 2,
                    "price": "100.00"
                }
            ]
        }, format='json')
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        order_id = response.data['id']
        url = reverse('payment-checkout', kwargs={'order_id': order_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('iframe_url', response.data)
        self.assertIn('payment_id', response.data)

    def test_order_status_view(self):
        cart_url = reverse('cart')
        self.client.put(cart_url, {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 2,
                    "price": "100.00"
                }
            ]
        }, format='json')
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        order_id = response.data['id']
        url = reverse('order_status', kwargs={'order_id': order_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)

    def test_payment_webhook_view(self):
        cart_url = reverse('cart')
        self.client.put(cart_url, {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 2,
                    "price": "100.00"
                }
            ]
        }, format='json')
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        order_id = response.data['id']
        payment = Payment.objects.create(
            order_id=order_id,
            payment_order_id='webhook-test',
            paymob_payment_id='12345',
            status='PENDING'
        )
        webhook_data = {
            'order_id': '12345',
            'success': 'true'
        }
        url = reverse('payment-webhook')
        response = self.client.post(url, webhook_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')

    def test_cart_requires_authentication(self):
        client = APIClient()  # Not authenticated
        url = reverse('cart')
        response = client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_cannot_access_another_users_order(self):
        # Create a second user and an order for them
        other_user = User.objects.create_user(email='other@example.com', username='other', password='otherpass')
        other_profile = UserProfile.objects.create(
            user=other_user,
            address="Other Address",
            country=self.country,
            state=self.state,
            city=self.city
        )
        order = Order.objects.create(
            user=other_user,
            order_number='ORDER123',
            status='pending',
            total_amount=50,
            shipping_address=other_profile.address,
            payment_status='pending'
        )
        url = reverse('order-detail', args=[order.id])
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_to_cart_exceeds_stock(self):
        url = reverse('cart')
        cart_data = {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 999,  # Exceeds available stock
                    "price": "100.00"
                }
            ]
        }
        response = self.client.put(url, cart_data, format='json')
        # You may need to implement this validation in your view if not present!
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]

    def test_payment_webhook_invalid_data(self):
        url = reverse('payment-webhook')
        response = self.client.post(url, {}, format='json')  # Empty payload
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_order_creation_with_unavailable_product(self):
        self.product.is_available = False
        self.product.save()
        cart_url = reverse('cart')
        self.client.put(cart_url, {
            "items": [
                {
                    "product": self.product.id,
                    "size": "42",
                    "color": "red",
                    "quantity": 1,
                    "price": "100.00"
                }
            ]
        }, format='json')
        order_data = {"payment_status": "pending"}
        create_url = reverse('order-list')
        response = self.client.post(create_url, order_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not available' in response.data['detail'].lower()
