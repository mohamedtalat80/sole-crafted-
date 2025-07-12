from django.shortcuts import get_object_or_404
from django.shortcuts import render
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly,IsAuthenticated
from django.db import models
from .models import Product, Favorite, Rating
from .serialzers import HomeProductSerializer, ProductDetailsSerializer, FavoriteSerializer
from rest_framework.response import Response
from rest_framework import status   
from rest_framework.views import APIView
from rest_framework import permissions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class HomeProductListView(ListAPIView):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = HomeProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductDetailsView(RetrieveAPIView):  
    queryset = Product.objects.all()
    serializer_class = ProductDetailsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]




class AddToFavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Add a product to user's favorites",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product_id'],
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID to add to favorites')
            }
        ),
        responses={
            201: openapi.Response(
                description="Product added to favorites",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            200: openapi.Response(
                description="Product already in favorites",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Product not found")
        }
    )
    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        user = request.user

        favorite, created = Favorite.objects.get_or_create(user=user, product=product)

        if created:
            return Response({'message': 'Added to favorites'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Already in favorites'}, status=status.HTTP_200_OK)


class RemoveFromFavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Remove a product from user's favorites",
        responses={
            200: openapi.Response(
                description="Product removed from favorites",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Product not found or not in favorites")
        }
    )
    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        user = request.user

        try:
            favorite = Favorite.objects.get(user=user, product=product)
            favorite.delete()
            return Response({'message': 'Removed from favorites'}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({'message': 'Not in favorites'}, status=status.HTTP_404_NOT_FOUND)


class CheckFavoriteStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check if a product is in user's favorites",
        responses={
            200: openapi.Response(
                description="Favorite status retrieved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_in_favorites': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Product not found")
        }
    )
    def get(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk)
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        return Response({'is_in_favorites': is_favorite})


class ListFavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all user's favorite products",
        responses={
            200: FavoriteSerializer(many=True),
            401: openapi.Response(description="Unauthorized")
        }
    )
    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user)
        serializer = FavoriteSerializer(favorites, many=True)
        return Response(serializer.data)
    
class ProductRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get product rating",
        responses={
            200: openapi.Response(
                description="Product rating retrieved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'rating': openapi.Schema(type=openapi.TYPE_NUMBER, description='Average rating (0-5)')
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Product not found")
        }
    )
    def get(self, request, pk):
        """Get product rating"""
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get average rating from related Rating model
        ratings = Rating.objects.filter(product=product)
        if ratings.exists():
            avg_rating = ratings.aggregate(avg_rating=models.Avg('rating'))['avg_rating']
            return Response({'rating': round(avg_rating, 2)}, status=status.HTTP_200_OK)
        else:
            return Response({'rating': 0}, status=status.HTTP_200_OK)

class ProductCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get product comments",
        responses={
            200: openapi.Response(
                description="Product comments retrieved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'comments': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'user': openapi.Schema(type=openapi.TYPE_STRING),
                                    'comment': openapi.Schema(type=openapi.TYPE_STRING),
                                    'rating': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Product not found")
        }
    )
    def get(self, request, pk):
        """Get product comments"""
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get comments from related Rating model
        comments = Rating.objects.filter(product=product, comment__isnull=False).exclude(comment='')
        comments_data = [{'user': rating.user.username, 'comment': rating.comment, 'rating': rating.rating, 'created_at': rating.created_at} for rating in comments]
        return Response({'comments': comments_data}, status=status.HTTP_200_OK)


