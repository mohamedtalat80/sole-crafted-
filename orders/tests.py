from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from Prouducts.models import Product, Category
from .models import Cart, CartItem, Order, OrderItem

User = get_user_model()

class CartOrderAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com',username='testuser', password='testpass123')
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

    def test_cart_lifecycle(self):
        # Ensure cart is empty
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])
        # Batch update cart
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
        response = self.client.put('/api/cart/', cart_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(float(response.data['total_amount']), 200.00)
        # Clear cart
        response = self.client.delete('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_order_creation_and_retrieval(self):
        # Add item to cart
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
        self.client.put('/api/cart/', cart_data, format='json')
        # Create order
        order_data = {
            "shipping_address": "123 Test St",
            "billing_address": "123 Test St",
            "payment_status": "paid"
        }
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data['id']
        self.assertEqual(response.data['total_amount'], '200.00')
        # List orders
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        # Retrieve order detail
        response = self.client.get(f'/api/orders/{order_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order_id)

    def test_cart_cleared_after_order(self):
        # Add item to cart
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
        self.client.put('/api/cart/', cart_data, format='json')
        # Create order
        order_data = {
            "shipping_address": "123 Test St",
            "billing_address": "123 Test St",
            "payment_status": "paid"
        }
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Cart should be empty after order
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_order_creation_with_empty_cart_fails(self):
        # Ensure cart is empty
        response = self.client.get('/api/cart/')
        self.assertEqual(response.data['items'], [])
        # Try to create order
        order_data = {
            "shipping_address": "123 Test St",
            "billing_address": "123 Test St",
            "payment_status": "paid"
        }
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cart is empty', response.data['detail'])

    def test_cart_is_user_specific(self):
        # Add item to first user's cart
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
        self.client.put('/api/cart/', cart_data, format='json')
        # Create a second user
        user2 = User.objects.create_user(email='user2@example.com', username='user2', password='testpass456')
        self.client.force_authenticate(user=user2)
        # Second user's cart should be empty
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])
        # Add item to second user's cart
        cart_data2 = {
            "items": [
                {
                    "product": self.product.id,
                    "size": "43",
                    "color": "blue",
                    "quantity": 1,
                    "price": "100.00"
                }
            ]
        }
        self.client.put('/api/cart/', cart_data2, format='json')
        # First user's cart should remain unchanged
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/cart/')
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['size'], '42')

    def test_order_is_immutable(self):
        # Add item to cart and create order
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
        self.client.put('/api/cart/', cart_data, format='json')
        order_data = {
            "shipping_address": "123 Test St",
            "billing_address": "123 Test St",
            "payment_status": "paid"
        }
        response = self.client.post('/api/orders/', order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data['id']
        # Try to update the order (should not be allowed, expect 405 or 403)
        patch_data = {"status": "cancelled"}
        patch_response = self.client.patch(f'/api/orders/{order_id}/', patch_data, format='json')
        self.assertIn(patch_response.status_code, [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
