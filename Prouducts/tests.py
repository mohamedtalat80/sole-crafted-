from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import Product, Category

# Create your tests here.

class ProductAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Sneakers")
        self.product = Product.objects.create(
            name="Test Shoe",
            brand="Test Brand",
            description="A test shoe.",
            price=1100.00,
            discount_percentage=10,
            main_image="http://example.com/image.jpg",
            sizes={"42": 5, "43": 3},
            colors={"red": 2, "blue": 1},
            category=self.category,
            is_available=True,
            stock_quantity=10
        )

    def test_home_product_list(self):
        url = reverse('home-products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print (response.data)
        print (self.product.price)
        self.assertTrue(any(p['name'] == self.product.name for p in response.data))

    def test_product_details(self):
        url = reverse('product-details', args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.product.name)
