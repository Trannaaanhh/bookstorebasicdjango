from django.urls import path
from store.controllers import cartController

urlpatterns = [
    path('', cartController.view_cart, name='cart_view'),
    path('add/<int:book_id>/', cartController.add_to_cart, name='cart_add'),
    path('remove/<int:item_id>/', cartController.remove_from_cart, name='cart_remove'),
]
