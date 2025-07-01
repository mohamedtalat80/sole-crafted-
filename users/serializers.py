from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, EmailVerification, PasswordResetOTP

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'password', 'confirm_password')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            password=validated_data['password'],
        )
        return user
class VerifyingEmailForUnVerifiedSerializer(serializers.Serializer):
    email=serializers.EmailField()
class EmailVerificationSerializer(serializers.Serializer):
    email=serializers.EmailField()
    code = serializers.CharField(max_length=6)

class PasswordResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return data

class UserSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # First authenticate the user
        data = super().validate(attrs)
        
        # Only include essential verification status
        data['verification_required'] = not self.user.is_verified
        
        # Optional: Include a simple message
        if not self.user.is_verified:
            data['message'] = "Please verify your email to access all features."
        
        return data 