from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Nếu là giảm tiền cố định
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Đơn hàng tối thiểu
    max_uses = models.IntegerField(null=True, blank=True)  # None = không giới hạn
    current_uses = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Check if coupon is still valid"""
        now = timezone.now()
        if not self.active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True

    def __str__(self):
        return self.code
