from django.shortcuts import render
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly,IsAuthenticated
from .models import Product
from .serialzers import HomeProductSerializer, ProductDetailsSerializer
from rest_framework.response import Response
from rest_framework import status   
class HomeProductListView(ListAPIView):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = HomeProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, *args, **kwargs):
        products = self.get_queryset()
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
class ProductDetailsView(RetrieveAPIView):  
    queryset = Product.objects.all()
    serializer_class = ProductDetailsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)


