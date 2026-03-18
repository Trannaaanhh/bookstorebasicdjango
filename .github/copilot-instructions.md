# Copilot Instructions for BookStore

## Architecture Overview
**BookStore** is a Django 4.2 e-commerce demo with Function-Based Views (FBVs) and modularized URL routing. Data stored in SQLite (root-level `db.sqlite3`). DEBUG is ON; only local app is `store`. Settings in [bookstore/settings.py](bookstore/settings.py#L1-126).

## Project Structure & Conventions

### Routing & URL Organization
- Top-level router [bookstore/urls.py](bookstore/urls.py) mounts: `/admin/`, `/books/`, `/cart/`, `/orders/`, plus root `/` reusing book URLs
- **Per-domain routing**: Each feature gets its own URLconf under [store/urls/](store/urls) (e.g., `book_urls.py`, `cart_urls.py`, `order_urls.py`)
  - `book_urls.py` defines `book_list` and `book_detail` (named routes used in templates)
  - `order_urls.py` defines `checkout` (named route)
  - `customer_urls.py` and `staff_urls.py` exist but are empty placeholders
- All controllers use FBVs (not class-based views) under [store/controllers/](store/controllers)

### Data Model & Relationships
Core entities in [store/models/](store/models):
- **Book**: `title`, `author`, `price`, `stock_quantity` (searchable by title/author)
- **Customer**: ID-based, no Django auth integration; password is plain `CharField`
- **Cart/CartItem**: `Cart.is_active=True` marks open cart; `CartItem` links cart→book→quantity via ForeignKey
- **Order/Shipping/Payment**: 1:1 relationships; `Shipping.fee` is flat 30000; `Payment.status` defaults to `'Pending'`
- **Context processor** [store/context_processors.py](store/context_processors.py) injects `cart_item_count` into all templates by summing active cart item quantities

### Controllers & Business Logic

#### Books Flow ([bookController.py](store/controllers/bookController.py))
- `list_books(request)`: Query all books; filter by `q` param (searches `title__icontains` or `author__icontains`)
- `book_detail(request, pk)`: Display book + recommendations
  - **Recommendation algorithm**: Find all carts containing this book → collect other book IDs in those carts → return up to 4 distinct books (excludes current book)
  - Catches all exceptions and returns `[]` (soft error handling)

#### Cart Flow ([cartController.py](store/controllers/cartController.py))
- `view_cart(request)`: Renders active cart with line totals and grand total
- `add_to_cart(request, book_id)`: Get-or-create active cart for customer; increment quantity if item exists
  - Supports both HTTP (redirects to `book_list`) and AJAX (returns JSON with `cart_count`)
  - Uses `_get_customer()` helper to fetch first customer (demo-only, unauthenticated)

#### Checkout Flow ([orderController.py](store/controllers/orderController.py))
- `checkout(request)`: GET displays checkout form with shipping/payment options; POST commits transaction
  - GET: Calculates `total_price = sum(item.book.price * item.quantity for item in cart.items)`
  - POST: Creates `Order` → `Shipping` (method + fee 30000) → `Payment` (status `'Pending'`) → marks cart `is_active=False`
  - Renders `store/cart/empty.html` (no active cart), `store/order/checkout.html` (form), or `store/order/success.html` (post-order)
  - ⚠ Context keys: `cart`, `total_price`, `shipping_methods`, `payment_methods` for checkout template

### Templates & View Paths
**Existing** (templates only):
- [book/list.html](store/templates/book/list.html): Displays `books` + search `query`
- [book/detail.html](store/templates/book/detail.html): Shows book + `recommendations`
- [store/base.html](store/templates/store/base.html): Base template (CSS/layout shared)

**Missing** (must create before testing flows):
- `store/cart/empty.html`: Empty cart view
- `store/cart/detail.html`: Cart items + line totals
- `store/order/checkout.html`: Form with shipping/payment dropdowns
- `store/order/success.html`: Order confirmation (receives `order` context)

### Development Workflow

**Local setup**:
```bash
cd soucrecode  # Always run from project root
python manage.py migrate  # Run after any model changes
python manage.py runserver  # Starts on http://localhost:8000/
```

**Adding features**:
1. Modify models in [store/models/](store/models)
2. Create migrations: `python manage.py makemigrations`
3. Run: `python manage.py migrate`
4. Add controller function in [store/controllers/](store/controllers)
5. Wire URL in appropriate [store/urls/*.py](store/urls)
6. Create/update templates under [store/templates/](store/templates) matching `render()` calls
7. ℹ Context processor auto-injects `cart_item_count`; use it in navbar

### Critical Details & Gotchas
- **No authentication**: `Cart` lookup picks `Customer.objects.first()` (hardcoded to first DB customer)
- **Cart semantics**: Always query `is_active=True` to avoid multiple open carts per customer
- **Order closure**: Checkout sets `cart.is_active=False` after order creation; customer needs new cart for next purchase
- **Recommendation safety**: `recommend_books()` is wrapped in try-except; returns `[]` on any error (silent fail)
- **Admin not registered**: No models in admin interface; modify [store/admin.py](store/admin.py) to expose models
- **Testing**: [store/tests.py](store/tests.py) is empty; no test runner configured beyond Django defaults

### Common Patterns to Follow
- Use `_get_customer()` helper pattern for customer resolution (centralize auth later)
- Wrap business logic in try-except if soft failure is acceptable (e.g., recommendations)
- Return `JsonResponse` for AJAX, redirect for form POST (cart controller pattern)
- Always include `related_name` in FK/O2O to enable reverse queries (`order.shipping`, `cart.items`)
- Template context: Be explicit about required keys; check controller for source
