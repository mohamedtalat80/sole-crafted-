from django.contrib import admin
from .models import Order, OrderItem,Cart, CartItem, Country, State, City

# Register your models here.
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
