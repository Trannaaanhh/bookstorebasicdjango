from django.db import models
from .book import Book
from .order import Order


class InventoryLog(models.Model):
    ACTION_CHOICES = [
        ('add', 'Thêm hàng'),
        ('reduce', 'Giảm hàng'),
        ('reserve', 'Giữ hàng'),
        ('restore', 'Hoàn trả'),
        ('adjustment', 'Điều chỉnh'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='inventory_logs')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity_change = models.IntegerField()  # Có thể âm
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)  # VD: "Khách hủy đơn", "Kiểm kho"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.book.title} - {self.action} ({self.quantity_change})"
