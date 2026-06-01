from rest_framework import serializers
from .models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'address', 'country', 'state', 'city', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        # Handle user data if provided
        user_data = {}
        for field in ['first_name', 'last_name', 'email']:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)
        
        # Update user if user data was provided
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        
        return super().update(instance, validated_data)

class UserAdressInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['country', 'state', 'city','address']
        extra_kwargs = {
            'user': {'read_only': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    