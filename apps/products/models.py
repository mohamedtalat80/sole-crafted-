from __future__ import annotations

from django.db import models


def upload_product_image(instance, filename):
    return f"products/{instance.name}/{filename}"


class Category(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Size"
        verbose_name_plural = "Sizes"

    def __str__(self) -> str:
        return self.name


class Colour(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Colour"
        verbose_name_plural = "Colours"

    def __str__(self) -> str:
        return self.name


class ColourTranslation(models.Model):
    colour = models.ForeignKey(Colour, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("colour", "language")

    def __str__(self) -> str:
        return f"{self.colour.name} [{self.language}]"



class Product(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField(default=0)
    main_image = models.ImageField(upload_to=upload_product_image, blank=True, null=True)
    sizes = models.ManyToManyField(Size, blank=True)
    colors = models.ManyToManyField(Colour, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class ProductTranslation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        unique_together = ("product", "language")

    def __str__(self) -> str:
        return f"{self.product.name} [{self.language}]"


class TagTranslation(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("tag", "language")

    def __str__(self) -> str:
        return f"{self.tag.name} [{self.language}]"


class CategoryTranslation(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("category", "language")

    def __str__(self) -> str:
        return f"{self.category.name} [{self.language}]"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=upload_product_image)

    def __str__(self) -> str:
        return f"Image for {self.product.name}"
