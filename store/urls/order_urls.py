from django.urls import path
from store.controllers import orderController

urlpatterns = [
    path('checkout/', orderController.checkout, name='checkout'),
]