from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import DashboardAdmin, AuditLog
from Prouducts.models import Product, Category
from orders.models import Order, OrderItem, Payment, Country, State, City
from user_profile.models import UserProfile
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class DashboardAdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': True,
                'payments': True,
                'analytics': True
            }
        )

    def test_dashboard_admin_creation(self):
        self.assertTrue(self.dashboard_admin.is_dashboard_admin)
        self.assertEqual(self.dashboard_admin.user, self.user)
        self.assertTrue(self.dashboard_admin.dashboard_permissions['products'])

class DashboardAuthenticationTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': True,
                'payments': True,
                'analytics': True
            }
        )

    def test_dashboard_login_success(self):
        url = reverse('dashboard:dashboard-login')
        data = {
            'email': 'admin@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_dashboard_login_invalid_credentials(self):
        url = reverse('dashboard:dashboard-login')
        data = {
            'email': 'admin@test.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_login_non_admin_user(self):
        # Create a regular user (not dashboard admin)
        regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@test.com',
            password='testpass123'
        )
        
        url = reverse('dashboard:dashboard-login')
        data = {
            'email': 'regular@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_auth_verify(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:dashboard-verify')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)

    def test_dashboard_logout(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:dashboard-logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class DashboardProductManagementTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': True,
                'payments': True,
                'analytics': True
            }
        )
        
        self.category = Category.objects.create(name='Sneakers')
        self.product = Product.objects.create(
            name='Test Shoe',
            brand='Test Brand',
            description='A test shoe',
            price=100.00,
            category=self.category,
            sizes={'42': 5, '43': 3},
            colors={'red': 2, 'blue': 1}
        )
        
        self.client.force_authenticate(user=self.user)

    def test_dashboard_product_list(self):
        url = reverse('dashboard:dashboard-products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 1)

    def test_dashboard_product_list_with_filters(self):
        url = reverse('dashboard:dashboard-products')
        response = self.client.get(url, {
            'status': 'available',
            'category': self.category.id,
            'search': 'Test'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dashboard_product_detail(self):
        url = reverse('dashboard:dashboard-product-detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['name'], 'Test Shoe')

    def test_dashboard_product_create(self):
        url = reverse('dashboard:dashboard-products')
        data = {
            'name': 'New Shoe',
            'brand': 'New Brand',
            'description': 'A new shoe',
            'price': 150.00,
            'category': self.category.id,
            'sizes': {'44': 3},
            'colors': {'green': 1},
            'is_available': True,
            'stock_quantity': 10
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_dashboard_product_update(self):
        url = reverse('dashboard:dashboard-product-detail', args=[self.product.id])
        data = {
            'name': 'Updated Shoe',
            'price': 120.00
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Shoe')

    def test_dashboard_product_delete(self):
        url = reverse('dashboard:dashboard-product-detail', args=[self.product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Product.objects.count(), 0)

class DashboardOrderManagementTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': True,
                'payments': True,
                'analytics': True
            }
        )
        
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Sneakers')
        self.product = Product.objects.create(
            name='Test Shoe',
            brand='Test Brand',
            description='A test shoe',
            price=100.00,
            category=self.category,
            stock_quantity=10
        )
        
        self.country = Country.objects.create(name='Test Country', iso2='TC')
        self.state = State.objects.create(name='Test State', country=self.country)
        self.city = City.objects.create(name='Test City', state=self.state)
        
        self.order = Order.objects.create(
            user=self.customer,
            order_number='TEST123',
            status='pending',
            total_amount=200.00,
            shipping_address='Test Address',
            payment_status='pending'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='42',
            color='red',
            quantity=2,
            price_at_purchase=100.00
        )
        
        self.client.force_authenticate(user=self.user)

    def test_dashboard_order_list(self):
        url = reverse('dashboard:dashboard-orders')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 1)

    def test_dashboard_order_list_with_filters(self):
        url = reverse('dashboard:dashboard-orders')
        response = self.client.get(url, {
            'status': 'pending',
            'payment_status': 'pending',
            'customer': 'customer'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dashboard_order_detail(self):
        url = reverse('dashboard:dashboard-order-detail', args=[self.order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['order_number'], 'TEST123')

    def test_dashboard_order_update(self):
        url = reverse('dashboard:dashboard-order-detail', args=[self.order.id])
        data = {
            'status': 'processing',
            'shipping_address': 'Updated Address'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'processing')

    def test_dashboard_order_cancel(self):
        url = reverse('dashboard:dashboard-order-detail', args=[self.order.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')

class DashboardAnalyticsTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': True,
                'payments': True,
                'analytics': True
            }
        )
        
        self.client.force_authenticate(user=self.user)

    def test_dashboard_overview(self):
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('sales', response.data['data'])
        self.assertIn('orders', response.data['data'])
        self.assertIn('products', response.data['data'])
        self.assertIn('payments', response.data['data'])

    def test_dashboard_analytics(self):
        url = reverse('dashboard:dashboard-analytics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

class DashboardPermissionsTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            is_active=True,
            is_verified=True
        )
        
        # Create admin with limited permissions
        self.dashboard_admin = DashboardAdmin.objects.create(
            user=self.user,
            is_dashboard_admin=True,
            dashboard_permissions={
                'products': True,
                'orders': False,
                'payments': False,
                'analytics': False
            }
        )

    def test_product_permission_allowed(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:dashboard-products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_order_permission_denied(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:dashboard-orders')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_analytics_permission_denied(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:dashboard-analytics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 