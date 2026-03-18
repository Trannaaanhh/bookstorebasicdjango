"""Utility/demo classes with lightweight implementations.

These helpers are intentionally simple and side-effect safe; callers can
layer additional logic as needed.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List

from django.db import transaction

from store.models import Book, Cart, CartItem


class InventoryService:
    def reserve_stock(self, book_id: int, quantity: int, order_id: int | None = None, reason: str = "") -> bool:
        """Decrease stock if available; log to InventoryLog; return True on success."""
        if quantity <= 0:
            return False

        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(pk=book_id)
                if book.stock_quantity < quantity:
                    return False
                
                stock_before = book.stock_quantity
                book.stock_quantity -= quantity
                book.save(update_fields=["stock_quantity"])
                
                # Log to InventoryLog
                from store.models import InventoryLog, Order
                log_order = None
                if order_id:
                    try:
                        log_order = Order.objects.get(pk=order_id)
                    except Order.DoesNotExist:
                        pass
                
                InventoryLog.objects.create(
                    book=book,
                    order=log_order,
                    action='reduce',
                    quantity_change=-quantity,
                    stock_before=stock_before,
                    stock_after=book.stock_quantity,
                    reason=reason or "Đặt hàng"
                )
            return True
        except Book.DoesNotExist:
            return False

    def restore_stock(self, book_id: int, quantity: int, order_id: int | None = None, reason: str = "") -> bool:
        """Restore stock when order is cancelled; log to InventoryLog."""
        if quantity <= 0:
            return False

        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(pk=book_id)
                stock_before = book.stock_quantity
                book.stock_quantity += quantity
                book.save(update_fields=["stock_quantity"])
                
                from store.models import InventoryLog, Order
                log_order = None
                if order_id:
                    try:
                        log_order = Order.objects.get(pk=order_id)
                    except Order.DoesNotExist:
                        pass
                
                InventoryLog.objects.create(
                    book=book,
                    order=log_order,
                    action='restore',
                    quantity_change=quantity,
                    stock_before=stock_before,
                    stock_after=book.stock_quantity,
                    reason=reason or "Hoàn trả"
                )
            return True
        except Book.DoesNotExist:
            return False

    def get_low_stock_books(self, threshold: int = 10):
        """Get books with stock <= threshold."""
        return Book.objects.filter(stock_quantity__lte=threshold)


class PriceCalculator:
    def total_with_tax(self, subtotal: Decimal, tax_rate: float = 0.0) -> Decimal:
        """Calculate total including tax (tax_rate expressed as fraction, e.g., 0.1 for 10%)."""
        subtotal = self._to_decimal(subtotal)
        rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")
        return (subtotal * (Decimal("1") + rate)).quantize(Decimal("0.01"))

    @staticmethod
    def _to_decimal(value) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class DiscountPolicy:
    def apply_discount(self, subtotal: Decimal) -> Decimal:
        """Apply a simple discount: 5% off for orders >= 500000."""
        subtotal = PriceCalculator._to_decimal(subtotal)
        if subtotal >= Decimal("500000"):
            return (subtotal * Decimal("0.95")).quantize(Decimal("0.01"))
        return subtotal

    def apply_coupon(self, subtotal: Decimal, coupon_code: str | None = None) -> tuple[Decimal, str]:
        """Apply coupon if valid; return (discounted_subtotal, message)"""
        if not coupon_code:
            return self.apply_discount(subtotal), ""
        
        try:
            from store.models import Coupon
            coupon = Coupon.objects.get(code=coupon_code)
            
            if not coupon.is_valid():
                return self.apply_discount(subtotal), "Mã giảm giá không còn hợp lệ"
            
            subtotal = PriceCalculator._to_decimal(subtotal)
            if subtotal < coupon.min_order_value:
                return subtotal, f"Đơn hàng tối thiểu {coupon.min_order_value:,.0f}đ"
            
            # Apply coupon discount
            if coupon.discount_percent > 0:
                discount_amount = subtotal * (Decimal(str(coupon.discount_percent)) / Decimal("100"))
            elif coupon.discount_amount:
                discount_amount = Decimal(str(coupon.discount_amount))
            else:
                discount_amount = Decimal("0")
            
            result = (subtotal - discount_amount).quantize(Decimal("0.01"))
            coupon.current_uses += 1
            coupon.save(update_fields=["current_uses"])
            
            return result, f"Đã áp dụng mã '{coupon_code}'"
        except Exception as e:
            return self.apply_discount(subtotal), f"Lỗi: {str(e)}"



class RecommendationEngine:
    def recommend(self, book_id: int, limit: int = 4):
        """Recommend books that co-occur in carts with the given book."""
        related = CartItem.objects.filter(book_id=book_id)
        cart_ids = [c.cart_id for c in related]
        if not cart_ids:
            return []
        items = CartItem.objects.filter(cart_id__in=cart_ids)
        book_ids = [i.book_id for i in items]
        return Book.objects.filter(id__in=book_ids).exclude(id=book_id).distinct()[:limit]


class CartValidator:
    def validate(self, cart_id: int) -> List[str]:
        """Return validation errors; empty list when cart is ready for checkout."""
        errors: List[str] = []
        cart = Cart.objects.filter(id=cart_id, is_active=True).first()
        if not cart:
            return ["Giỏ hàng không tồn tại hoặc đã đóng."]

        items = list(cart.items.select_related("book"))
        if not items:
            return ["Giỏ hàng trống."]

        for item in items:
            if item.quantity <= 0:
                errors.append(f"Số lượng không hợp lệ cho {item.book.title}.")
            if item.book.stock_quantity < item.quantity:
                errors.append(f"Không đủ hàng cho {item.book.title}.")
        return errors


class CheckoutContext:
    shipping_methods = ["Giao hàng nhanh", "Giao hàng tiết kiệm"]
    payment_methods = ["COD", "Banking"]

    def build(self, cart_id: int) -> dict:
        """Assemble checkout data (cart, items, totals, methods)."""
        cart = Cart.objects.filter(id=cart_id, is_active=True).prefetch_related("items__book").first()
        
        if not cart:
            return {
                "cart": None,
                "items": [],
                "total_price": Decimal("0"),
                "shipping_methods": self.shipping_methods,
                "payment_methods": self.payment_methods,
                "shipping_fee": Decimal("0"),
                "grand_total": Decimal("0"),
            }

        items = [
            {"obj": item, "line_total": item.book.price * item.quantity}
            for item in cart.items.all()
        ]
        total_price = sum(data["line_total"] for data in items)
        shipping_fee = ShippingCalculator().compute_fee(self.shipping_methods[0]) if items else Decimal("0")
        grand_total = total_price + shipping_fee

        return {
            "cart": cart,
            "items": items,
            "total_price": total_price,
            "shipping_methods": self.shipping_methods,
            "payment_methods": self.payment_methods,
            "shipping_fee": shipping_fee,
            "grand_total": grand_total,
        }


class ShippingCalculator:
    def compute_fee(self, method: str) -> Decimal:
        """Return a fee for the given shipping method."""
        method_normalized = (method or "").lower()
        if "nhanh" in method_normalized:
            return Decimal("30000")
        if "tiết" in method_normalized or "tiet" in method_normalized:
            return Decimal("20000")
        return Decimal("25000")


class PaymentGatewayStub:
    def charge(self, amount: Decimal, token: str | None = None) -> str:
        """Pretend to charge; always succeeds and returns a transaction ID."""
        return f"TXN-{uuid.uuid4()}"


class NotificationService:
    def send_order_confirmation(self, customer_id: int, order_id: int) -> None:
        """Simulate sending an order confirmation (stdout/no-op)."""
        print(f"[notify] order {order_id} confirmed for customer {customer_id}")


class AuditLogger:
    def log_event(self, event: str, payload: dict | None = None) -> None:
        """Record an audit event (stdout/no-op)."""
        print(f"[audit] {event} | payload={payload or {}}")
