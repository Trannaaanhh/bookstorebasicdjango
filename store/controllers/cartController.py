from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from store.models import Cart, CartItem, Customer, Book
from store.utils.demo_classes import InventoryService

inventory_service = InventoryService()


def _get_customer():
    return Customer.objects.first()


def view_cart(request):
    customer = _get_customer()
    if not customer:
        return render(request, 'store/cart/empty.html')

    cart = Cart.objects.filter(customer=customer, is_active=True).first()
    if not cart or not cart.items.exists():
        return render(request, 'store/cart/empty.html')

    items = [{
        'obj': item,
        'line_total': item.book.price * item.quantity
    } for item in cart.items.all()]

    total_price = sum(data['line_total'] for data in items)
    context = {
        'cart': cart,
        'items': items,
        'total_price': total_price,
    }
    return render(request, 'store/cart/detail.html', context)


def add_to_cart(request, book_id):
    customer = _get_customer()
    if not customer:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No customer', 'cart_count': 0})
        return redirect('book_list')

    book = get_object_or_404(Book, pk=book_id)
    
    if book.stock_quantity <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Out of stock', 'cart_count': 0})
        return redirect('book_detail', pk=book_id)
    
    cart, _ = Cart.objects.get_or_create(customer=customer, is_active=True)
    item, created = CartItem.objects.get_or_create(cart=cart, book=book, defaults={'quantity': 1})
    if not created:
        item.quantity += 1
        item.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item.quantity for item in cart.items.all())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('book_list')


def remove_from_cart(request, item_id):
    customer = _get_customer()
    if not customer:
        return redirect('book_list')

    item = CartItem.objects.filter(id=item_id, cart__customer=customer, cart__is_active=True).first()
    if item:
        item.delete()

    return redirect('cart_view')
