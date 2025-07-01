from django.db import models
from users.models import User
class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    brand= models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField(default=0)
    main_image = models.URLField(max_length=255, blank=True, null=True)
    sizes = models.JSONField(default=dict)
    colors = models.JSONField(default=dict)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True)
    stock_quantity = models.IntegerField(default=0)
    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    def __str__(self):
        return f"Image for {self.product.name}"
class Rating(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='rating')
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    




