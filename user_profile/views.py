from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserProfile
from .serializers import UserProfileSerializer
from django.db import transaction
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .serializers import UserProfileSerializer,UserProfileCreateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get user profile information",
        responses={
            200: UserProfileSerializer,
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Profile not found")
        }
    )
    def get(self, request):
        user_profile = UserProfile.objects.get(user=request.user)
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update user profile information",
        request_body=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Profile not found")
        }
    )
    def put(self, request):
        user_profile = get_object_or_404(UserProfile, user=request.user)
        serializer = UserProfileSerializer(user_profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Partially update user profile information",
        request_body=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Profile not found")
        }
    )
    def patch(self, request):
        user_profile = get_object_or_404(UserProfile, user=request.user)
        serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get user information",
        responses={
            200: UserProfileCreateSerializer,
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User info not found")
        }
    )
    def get(self, request):
        user_info=get_object_or_404(UserProfile,user=request.user)
        serializer = UserProfileCreateSerializer(user_info)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create or update user information",
        request_body=UserProfileCreateSerializer,
        responses={
            200: UserProfileCreateSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User info not found")
        }
    )
    def post(self, request):
        user_info=get_object_or_404(UserProfile,user=request.user)
        serializer = UserProfileCreateSerializer(user_info, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Update user information",
        request_body=UserProfileCreateSerializer,
        responses={
            200: UserProfileCreateSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User info not found")
        }
    )
    def put(self, request):
        user_info=get_object_or_404(UserProfile,user=request.user)
        serializer = UserProfileCreateSerializer(user_info, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# Create your views here.
