from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import UserProfile
from orders.models import Country, State, City
from Prouducts.models import Product, Category, Favorite
from django.utils.crypto import get_random_string

User = get_user_model()

class UserProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@test.com',password='testpass',is_active=True,is_verified=True)
        self.country = Country.objects.create(name='CountryA', iso2='CA')
        self.state = State.objects.create(name='StateA', country=self.country)
        self.city = City.objects.create(name='CityA', state=self.state)
        self.profile = UserProfile.objects.create(user=self.user, address='Addr', country=self.country, city=self.city)
        self.client.force_authenticate(user=self.user)

    def test_get_user_profile_authenticated(self):
        url = reverse('user-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], self.user.id)
        self.assertIn('address', response.data)
        self.assertIn('country', response.data)
        self.assertIn('state', response.data)
        self.assertIn('city', response.data)
        self.assertIn('is_default', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        self.assertNotIn('orders', response.data)
        self.assertNotIn('favorite_products', response.data)

    def test_get_user_profile_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('user-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_info_authenticated(self):
        url = reverse('user-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['address'], self.profile.address)

    def test_get_user_info_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('user-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_info_valid(self):
        url = reverse('user-info')
        data = {
            'address': 'New Address',
            'country': self.country.id,
            'state': self.state.id,
            'city': self.city.id
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.address, 'New Address')

    def test_update_user_info_invalid_country(self):
        url = reverse('user-info')
        data = {
            'address': 'Addr',
            'country': 999,
            'state': self.state.id,
            'city': self.city.id
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_info_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('user-info')
        data = {
            'address': 'Addr',
            'country': self.country.id,
            'state': self.state.id,
            'city': self.city.id
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_info_missing_required_fields(self):
        url = reverse('user-info')
        data = {
            'address': 'New Address'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_info_invalid_state_for_country(self):
        other_country = Country.objects.create(name='CountryB', iso2='CB')
        other_state = State.objects.create(name='StateB', country=other_country)
        url = reverse('user-info')
        data = {
            'address': 'Addr',
            'country': self.country.id,
            'state': other_state.id,
            'city': self.city.id
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_user_info_valid(self):
        url = reverse('user-info')
        data = {
            'address': 'New Address',
            'country': self.country.id,
            'state': self.state.id,
            'city': self.city.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.address, 'New Address')

    def test_update_user_profile_put(self):
        url = reverse('user-profile')
        data = {
            'address': 'Updated Address',
            'country': self.country.id,
            'state': self.state.id,
            'city': self.city.id,
            'is_default': True
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.address, 'Updated Address')
        self.assertTrue(self.profile.is_default)

    def test_update_user_profile_patch(self):
        url = reverse('user-profile')
        data = {
            'address': 'Partially Updated Address'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.address, 'Partially Updated Address')
        self.assertEqual(self.profile.country, self.country)

    def test_update_user_profile_invalid_data(self):
        url = reverse('user-profile')
        data = {
            'address': 'Updated Address',
            'country': 999
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_profile_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('user-profile')
        data = {
            'address': 'Updated Address'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_user_profile_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('user-profile')
        data = {
            'address': 'Updated Address'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
