from django.contrib import admin
from store.models import Book, Customer, Cart, CartItem, Order, Shipping, Payment, Staff


admin.site.register(Book)
admin.site.register(Customer)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(Shipping)
admin.site.register(Payment)
admin.site.register(Staff)
