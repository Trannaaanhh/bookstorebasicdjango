from django.db import models
from .customer import Customer
from .staff import Staff

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    handled_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_handled')
    updated_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_updated')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='Pending')  # Pending, Processing, Shipped, Delivered, Cancelled
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Shipping(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipping')
    method_name = models.CharField(max_length=100) # VD: Giao hàng nhanh
    fee = models.DecimalField(max_digits=10, decimal_places=2)

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method_name = models.CharField(max_length=100) # VD: COD, Banking
    status = models.CharField(max_length=50, default='Pending')