from django.shortcuts import render, get_object_or_404
from .models import Category, Product

# If using Redis for recommendations:
# import redis
# from django.conf import settings
# r = redis.Redis(host=settings.REDIS_HOST,
#                 port=settings.REDIS_PORT,
#                 db=settings.REDIS_DB)


def home(request):
    """Display the home page with featured products and banners."""
    from .models import Banner
    banners = Banner.objects.filter(active=True)
    featured_products = Product.objects.filter(available=True, is_featured=True).select_related('category', 'brand').order_by('-id')[:4]
    categories = Category.objects.all()
    
    wishlisted_product_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        wishlisted_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'shop/home.html', {
        'banners': banners,
        'featured_products': featured_products,
        'categories': categories,
        'wishlisted_product_ids': wishlisted_product_ids,
    })


def about(request):
    """Render the ultra-premium About Us page with SVG animations."""
    return render(request, 'shop/about.html')


from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.utils import timezone

def product_list(request, category_slug=None):
    """List products, optionally filtered by category and GET parameters."""
    category = None
    categories = Category.objects.prefetch_related('brands').all()
    from django.db.models import Avg, Q
    products = Product.objects.filter(available=True).select_related('category', 'brand').annotate(avg_rating=Avg('reviews__rating'))

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
    # 1. Search Query
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # 2. Brands List (Multi-select - ignore empty values)
    selected_brands = [b for b in request.GET.getlist('brand') if b and b.strip()]
    if selected_brands:
        products = products.filter(brand__slug__in=selected_brands)

    # 3. Price Range (with secure validation)
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (ValueError, InvalidOperation):
            pass
            
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (ValueError, InvalidOperation):
            pass

    # 4. Flags (On Sale, In Stock)
    if request.GET.get('on_sale') == 'true':
        now = timezone.now()
        products = products.filter(
            sale_price__isnull=False,
            sale_start__lte=now,
            sale_end__gte=now
        )
        
    if request.GET.get('in_stock') == 'true':
        products = products.filter(stock_quantity__gt=0)
        
    # 5. Rating Filter
    min_rating = request.GET.get('min_rating', '').strip()
    if min_rating:
        try:
            products = products.filter(avg_rating__gte=int(min_rating))
        except ValueError:
            pass

    # 6. Sorting
    sort_by = request.GET.get('sort', '')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating', '-created')
    else:
        products = products.order_by('-id') # Default ordering
        
    from .models import Brand
    brands = Brand.objects.all()

    # 7. Pagination (12 products per page for optimal performance)
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    try:
        products_page = paginator.page(page_number)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    wishlisted_product_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        wishlisted_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'brands': brands,
        'products': products_page,
        'selected_brands': selected_brands,
        'wishlisted_product_ids': wishlisted_product_ids,
    })


def product_detail(request, id, slug):
    """Display a single product with add-to-cart form."""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('images'),
        id=id, slug=slug, available=True
    )
    # Import here to avoid circular imports
    from cart.forms import CartAddProductForm
    cart_product_form = CartAddProductForm()

    in_wishlist = False
    if request.user.is_authenticated:
        from .models import Wishlist
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    from .forms import ReviewForm
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            from django.db import IntegrityError
            try:
                review.save()
            except IntegrityError:
                pass
            return redirect('shop:product_detail', id=product.id, slug=product.slug)
    else:
        review_form = ReviewForm()

    reviews = product.reviews.select_related('user').all()
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()

    # Rating breakdown calculation
    from django.db.models import Count
    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    counts_qs = reviews.values('rating').annotate(c=Count('id'))
    for row in counts_qs:
        rating_counts[row['rating']] = row['c']
        
    total_reviews = reviews.count()
    rating_percentages = {}
    for r in range(1, 6):
        pct = (rating_counts[r] / total_reviews * 100) if total_reviews > 0 else 0
        rating_percentages[r] = round(pct)

    # Verified buyers
    from orders.models import OrderItem
    verified_user_ids = set(
        OrderItem.objects.filter(product=product, order__user__isnull=False)
        .values_list('order__user_id', flat=True)
    )

    return render(request, 'shop/product/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'in_wishlist': in_wishlist,
        'review_form': review_form,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'total_reviews': total_reviews,
        'rating_percentages': rating_percentages,
        'verified_user_ids': verified_user_ids,
    })


def product_recommender(request, product_id):
    """
    Return a partial template with recommended products.
    Designed to be called via HTMX with hx-trigger="revealed"
    for lazy loading.
    
    This analyzes actual order history to find 'Frequently Bought Together' products.
    """
    from orders.models import OrderItem
    from django.db.models import Count
    
    product = get_object_or_404(Product, id=product_id, available=True)
    recommended = []

    # 1. Find all orders that contain this product
    order_ids = OrderItem.objects.filter(product=product).values_list('order_id', flat=True)
    
    if order_ids:
        # 2. Find other products in those exact same orders, sort by frequency
        frequently_bought = OrderItem.objects.filter(order_id__in=order_ids)\
            .exclude(product=product)\
            .values('product_id')\
            .annotate(purchase_count=Count('product_id'))\
            .order_by('-purchase_count')[:6]
            
        if frequently_bought:
            pids = [item['product_id'] for item in frequently_bought]
            # Fetch products
            recommended_qs = list(Product.objects.filter(id__in=pids, available=True).select_related('category', 'brand'))
            # Sort them by their frequency rank
            recommended_qs.sort(key=lambda p: pids.index(p.id))
            recommended = recommended_qs

    if not recommended:
        # Fallback: if no co-purchase history exists, show products from same category
        recommended = list(
            Product.objects.filter(
                category=product.category, available=True
            ).select_related('category', 'brand').exclude(id=product_id)[:6]
        )

    return render(request, 'shop/product/partials/recommender.html', {
        'recommended_products': recommended,
        'product': product,
    })


# --- Authentication Views ---
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import UserRegistrationForm
from .models import Wishlist
import json


def user_login(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', '')
            if not next_url or not url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                next_url = 'shop:home'
            return redirect(next_url)
    else:
        form = AuthenticationForm(request)
        
    return render(request, 'shop/login.html', {'form': form})


def user_register(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send welcome email
            try:
                from emails.services import NotificationService
                NotificationService.send_welcome_email(user)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send welcome email: {e}")
                
            login(request, user)
            return redirect('shop:home')
    else:
        form = UserRegistrationForm()
        
    return render(request, 'shop/register.html', {'form': form})


@login_required
def user_dashboard(request):
    """User dashboard showing account details and order history."""
    orders = request.user.orders.prefetch_related('items__product').all()
    return render(request, 'shop/dashboard.html', {'orders': orders})


@require_POST
def user_logout(request):
    logout(request)
    return redirect('shop:home')


# --- Wishlist Views ---
@login_required
def wishlist_detail(request):
    """Display the user's wishlist."""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product__category', 'product__brand')
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})


@require_POST
def wishlist_toggle(request, product_id):
    """
    Toggle a product in the wishlist via HTMX.
    Returns the updated heart icon.
    """
    if not request.user.is_authenticated:
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = f"{redirect('shop:login').url}?next={request.META.get('HTTP_REFERER', '/')}"
            return response
        return redirect(f"{redirect('shop:login').url}?next={request.META.get('HTTP_REFERER', '/')}")

    product = get_object_or_404(Product, id=product_id, available=True)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        wishlist_item.delete()
        in_wishlist = False
        message = f'"{product.name}" removed from wishlist.'
    else:
        Wishlist.objects.create(user=request.user, product=product)
        in_wishlist = True
        message = f'"{product.name}" added to wishlist!'
        
    if request.headers.get('HX-Request'):
        from django.template.loader import render_to_string
        
        count = Wishlist.objects.filter(user=request.user).count()
        hidden_class = "hidden" if count == 0 else ""
        counter_html = f"""
        <span id="wishlist-counter" hx-swap-oob="true" class="ml-2 w-5 h-5 flex items-center justify-center text-xs font-medium rounded-full bg-white text-black {hidden_class}">
            {count}
        </span>
        """
        
        if request.GET.get('source') == 'wishlist_page':
            # Remove the card entirely
            heart_html = ""
        else:
            heart_html = render_to_string('shop/partials/wishlist_heart.html', {
                'product': product,
                'in_wishlist': in_wishlist,
            }, request=request)
        
        response = HttpResponse(heart_html + counter_html)
        response['HX-Trigger'] = json.dumps({
            'toast': {
                'message': message,
                'type': 'success',
            }
        })
        return response


def search_autocomplete(request):
    """HTMX view for live search dropdown auto-suggest."""
    query = request.GET.get('q', '').strip()
    products = []
    if len(query) >= 2:
        from django.db.models import Q
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            available=True
        ).select_related('category', 'brand')[:5]
    return render(request, 'shop/partials/search_dropdown.html', {'products': products, 'query': query})


# --- Custom 404 Error Handler & Preview ---
def custom_404_view(request, exception=None):
    """Render custom cyberpunk 404 error page."""
    return render(request, 'shop/404.html', status=404)


def preview_404(request):
    """Development preview route for 404 page."""
    return render(request, 'shop/404.html')


# --- Product Battle / Duel Mode ---
from django.http import JsonResponse

def serialize_product_battle(product):
    if not product:
        return None
    specs_data = []
    for spec in product.specs.all():
        specs_data.append({
            'name': spec.name,
            'value': spec.value,
            'numeric_value': spec.numeric_value or 0,
            'unit': spec.unit,
            'icon': spec.icon,
        })
    image_url = product.image.url if product.image else ''
    return {
        'id': product.id,
        'name': product.name,
        'image': image_url,
        'price': str(product.current_price),
        'formatted_price': f"L.E {product.current_price:,.2f}",
        'rating': product.average_rating,
        'url': product.get_absolute_url(),
        'specs': specs_data,
    }


def product_battle(request):
    """Display the interactive Product Battle Arena page."""
    products = Product.objects.filter(available=True).select_related('category', 'brand').order_by('name')
    
    product_a_id = request.GET.get('a')
    product_b_id = request.GET.get('b')
    
    product_a = Product.objects.filter(id=product_a_id, available=True).prefetch_related('specs').first() if product_a_id else None
    product_b = Product.objects.filter(id=product_b_id, available=True).prefetch_related('specs').first() if product_b_id else None
    
    # Defaults if none selected
    if not product_a and products.exists():
        product_a = products.first()
    if not product_b and products.count() > 1:
        product_b = products[1]

    return render(request, 'shop/battle.html', {
        'products': products,
        'product_a': product_a,
        'product_b': product_b,
        'product_a_json': json.dumps(serialize_product_battle(product_a)),
        'product_b_json': json.dumps(serialize_product_battle(product_b)),
    })


def battle_specs_api(request, product_id):
    """Return JSON spec data for a single product to power live HTMX/Alpine battle updates."""
    product = get_object_or_404(Product.objects.prefetch_related('specs'), id=product_id, available=True)
    return JsonResponse(serialize_product_battle(product))

