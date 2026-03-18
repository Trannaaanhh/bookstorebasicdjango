from decimal import Decimal

from django.db import transaction
from django.shortcuts import render

from store.models import Cart, Customer, Order, Payment, Shipping
from store.utils.demo_classes import (
    AuditLogger,
    CartValidator,
    CheckoutContext,
    DiscountPolicy,
    InventoryService,
    PaymentGatewayStub,
    PriceCalculator,
    RecommendationEngine,
    ShippingCalculator,
)

inventory_service = InventoryService()
price_calculator = PriceCalculator()
discount_policy = DiscountPolicy()
cart_validator = CartValidator()
checkout_context = CheckoutContext()
shipping_calculator = ShippingCalculator()
payment_gateway = PaymentGatewayStub()
audit_logger = AuditLogger()


def checkout(request):
    customer = Customer.objects.first()
    cart = Cart.objects.filter(customer=customer, is_active=True).first()

    if not cart or not cart.items.exists():
        return render(request, "store/cart/empty.html")

    base_context = checkout_context.build(cart.id)

    if request.method == "POST":
        errors = cart_validator.validate(cart.id)
        shipping_method = request.POST.get("shipping_method") or base_context["shipping_methods"][0]
        payment_method = request.POST.get("payment_method") or base_context["payment_methods"][0]
        shipping_fee = shipping_calculator.compute_fee(shipping_method)

        subtotal = base_context["total_price"]
        discounted_total = discount_policy.apply_discount(subtotal)
        total_with_tax = price_calculator.total_with_tax(discounted_total)
        final_total = total_with_tax + shipping_fee

        if errors:
            base_context.update({"errors": errors, "shipping_fee": shipping_fee, "grand_total": final_total})
            return render(request, "store/order/checkout.html", base_context)

        try:
            with transaction.atomic():
                for item in cart.items.select_related("book"):
                    if not inventory_service.reserve_stock(item.book_id, item.quantity):
                        raise ValueError(f"Không đủ hàng cho {item.book.title}.")

                order = Order.objects.create(customer=customer, total_price=final_total)
                Shipping.objects.create(order=order, method_name=shipping_method, fee=shipping_fee)
                Payment.objects.create(order=order, method_name=payment_method, status="Pending")
                cart.is_active = False
                cart.save(update_fields=["is_active"])
        except ValueError as exc:
            errors.append(str(exc))
            base_context.update({"errors": errors, "shipping_fee": shipping_fee, "grand_total": final_total})
            return render(request, "store/order/checkout.html", base_context)

        transaction_id = payment_gateway.charge(final_total)
        audit_logger.log_event("checkout_success", {"order_id": order.id, "txn": transaction_id})
        return render(request, "store/order/success.html", {"order": order})

    return render(request, "store/order/checkout.html", base_context)
