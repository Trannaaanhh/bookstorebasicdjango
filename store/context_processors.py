from store.models import Cart, Customer


def cart_count(request):
    """Add cart item count to all templates"""
    try:
        customer = Customer.objects.first()
        if customer:
            cart = Cart.objects.filter(customer=customer, is_active=True).first()
            if cart:
                count = sum(item.quantity for item in cart.items.all())
                return {'cart_item_count': count}
    except:
        pass
    return {'cart_item_count': 0}
