from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # Changed to False by default

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    def save(self, *args, **kwargs):
        # Auto-activate admin users
        if self.is_staff or self.is_superuser:
            self.is_active = True
            self.is_verified = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def is_valid(self):
        # Code expires after 10 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.email} - {self.code}"

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def is_valid(self):
        # OTP expires after 10 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"
