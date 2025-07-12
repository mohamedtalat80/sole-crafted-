from django.urls import path
from .views import HomeProductListView, ProductDetailsView, AddToFavoritesView, RemoveFromFavoritesView, CheckFavoriteStatusView, ListFavoritesView, ProductRatingView, ProductCommentView
urlpatterns = [
    path('home-products/', HomeProductListView.as_view(), name='home-products'),
    path('products-details/<int:pk>/', ProductDetailsView.as_view(), name='product-details'),
    path('favorites/add', AddToFavoritesView.as_view(), name='add-to-favorites'),
    path('favorites/remove/<int:pk>/', RemoveFromFavoritesView.as_view(), name='remove-from-favorites'),
    path('favorites/check-favorite-status/<int:pk>/', CheckFavoriteStatusView.as_view(), name='check-favorite-status'),
    path('favorites/list', ListFavoritesView.as_view(), name='list-favorites'),
    path('product-rating/<int:pk>/', ProductRatingView.as_view(), name='product-rating'), 
    path('product-comment/<int:pk>/', ProductCommentView.as_view(), name='product-comment'),
    
]