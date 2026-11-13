from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product

# If using Redis for recommendations:
# import redis
# from django.conf import settings
# r = redis.Redis(host=settings.REDIS_HOST,
#                 port=settings.REDIS_PORT,
#                 db=settings.REDIS_DB)


def home(request):
    """Display the UX-first home page with instant search, categories, brands, and modular product tabs."""
    from .models import Banner, Brand
    from django.urls import reverse
    from django.utils import timezone

    banners = Banner.objects.filter(active=True)

    # 1. Featured Products (up to 8 items, graceful fallback)
    featured_products = list(
        Product.objects.filter(available=True, is_featured=True)
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )
    if len(featured_products) < 8:
        extra_prods = (
            Product.objects.filter(available=True)
            .exclude(id__in=[p.id for p in featured_products])
            .select_related('category', 'subcategory', 'brand')
            .order_by('-id')[:8 - len(featured_products)]
        )
        featured_products.extend(list(extra_prods))

    # 2. Hot Deals / On Sale (with fallback to best-priced available items)
    now = timezone.now()
    deals_products = list(
        Product.objects.filter(
            available=True,
            sale_price__isnull=False,
            sale_start__lte=now,
            sale_end__gte=now,
        )
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )
    if len(deals_products) < 4:
        extra_deals = (
            Product.objects.filter(available=True)
            .exclude(id__in=[p.id for p in deals_products])
            .select_related('category', 'subcategory', 'brand')
            .order_by('price')[:8 - len(deals_products)]
        )
        deals_products.extend(list(extra_deals))

    # 3. Category Tabs Queries (up to 8 products each)
    power_products = list(
        Product.objects.filter(available=True)
        .filter(
            Q(name__icontains='charger')
            | Q(name__icontains='cable')
            | Q(name__icontains='gan')
            | Q(name__icontains='power bank')
            | Q(name__icontains='powerbank')
            | Q(name__icontains='power strip')
            | Q(name__icontains='adapter')
            | Q(name__icontains='20w')
            | Q(name__icontains='30w')
            | Q(name__icontains='45w')
            | Q(name__icontains='65w')
            | Q(name__icontains='100w')
            | Q(name__icontains='140w')
        )
        .exclude(name__icontains='lark')
        .exclude(name__icontains='mic')
        .exclude(name__icontains='headphone')
        .exclude(name__icontains='earbud')
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )

    bag_products = list(
        Product.objects.filter(available=True)
        .filter(
            Q(category__slug__iexact='bags')
            | Q(name__icontains='backpack')
            | Q(name__icontains='sleeve')
            | Q(name__icontains='bange')
            | Q(name__icontains='bag')
        )
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )

    desk_products = list(
        Product.objects.filter(available=True)
        .filter(
            Q(category__slug__in=['Computer-accessories', 'graphic-tablet'])
            | Q(name__icontains='mouse')
            | Q(name__icontains='keyboard')
            | Q(name__icontains='tablet')
            | Q(name__icontains='hub')
            | Q(name__icontains='stand')
        )
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )

    network_products = list(
        Product.objects.filter(available=True)
        .filter(
            Q(category__slug__iexact='Network')
            | Q(name__icontains='router')
            | Q(name__icontains='mesh')
            | Q(name__icontains='tp-link')
            | Q(name__icontains='wifi')
        )
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )

    creator_products = list(
        Product.objects.filter(available=True)
        .filter(
            Q(category__slug__iexact='graphic-tablet')
            | Q(subcategory__slug__in=['content-creation', 'wireless-mics-audio'])
            | Q(name__icontains='tablet')
            | Q(name__icontains='osmo')
            | Q(name__icontains='tripod')
            | Q(name__icontains='lark')
            | Q(name__icontains='microphone')
        )
        .select_related('category', 'subcategory', 'brand')
        .order_by('-id')[:8]
    )

    # 4. Single Source of Truth Configuration for Homepage Product Tabs (Real Product Photos)
    catalog_url = reverse('shop:product_list')
    mobile_cat_url = reverse('shop:product_list_by_category', args=['mobile-accessories'])
    catalog_tabs = [
        {
            'key': 'featured',
            'image': 'img/categories/chargers.webp',
            'label_en': 'Most Popular',
            'label_ar': 'الأكثر طلباً',
            'products': featured_products,
            'more_url': catalog_url,
        },
        {
            'key': 'bags',
            'image': 'img/categories/backpacks.webp',
            'label_en': 'Bags & Sleeves',
            'label_ar': 'شنط وجرابات لابتوب',
            'products': bag_products,
            'more_url': reverse('shop:product_list_by_category', args=['bags']),
        },
        {
            'key': 'power',
            'image': 'img/categories/chargers.webp',
            'label_en': 'Chargers, Power & Cables',
            'label_ar': 'شواحن وباور بانك وكابلات',
            'products': power_products,
            'more_url': f"{mobile_cat_url}?subcategory=chargers-gan,power-banks,cables-adapters",
        },
        {
            'key': 'desk',
            'image': 'img/categories/mouse.webp',
            'label_en': 'Mice, Keyboards & Desk Gear',
            'label_ar': 'ماوس وكيبورد وإكسسوارات المكتب',
            'products': desk_products,
            'more_url': reverse('shop:product_list_by_category', args=['Computer-accessories']),
        },
        {
            'key': 'creators',
            'image': 'img/categories/tablets.webp',
            'label_en': 'Tablets, Gimbals & Mics',
            'label_ar': 'تابلت رسم ومعدات تصوير ومايكات',
            'products': creator_products,
            'more_url': f"{mobile_cat_url}?subcategory=content-creation,wireless-mics-audio",
        },
        {
            'key': 'network',
            'image': 'img/categories/routers.webp',
            'label_en': 'Routers & Networking',
            'label_ar': 'راوترات وشبكات',
            'products': network_products,
            'more_url': reverse('shop:product_list_by_category', args=['Network']),
        },
        {
            'key': 'deals',
            'image': 'img/categories/earbuds.webp',
            'label_en': 'Best Value & Deals',
            'label_ar': 'أفضل العروض',
            'products': deals_products,
            'more_url': f"{catalog_url}?sort=price_asc",
        },
    ]

    # 5. Single Source of Truth for Quick Search Pills (Real Miniature Product Photos)
    comp_cat_url = reverse('shop:product_list_by_category', args=['Computer-accessories'])
    bags_cat_url = reverse('shop:product_list_by_category', args=['bags'])
    net_cat_url = reverse('shop:product_list_by_category', args=['Network'])
    apple_cat_url = reverse('shop:product_list_by_category', args=['APPLE'])
    graphic_cat_url = reverse('shop:product_list_by_category', args=['graphic-tablet'])
    quick_searches = [
        {'image': 'img/categories/tablets.webp', 'label_en': 'Apple & iPad', 'label_ar': 'آيباد وأجهزة أبل', 'query': 'ipad', 'url': apple_cat_url},
        {'image': 'img/categories/backpacks.webp', 'label_en': 'Laptop Backpacks', 'label_ar': 'شنط لابتوب', 'query': 'backpack', 'url': bags_cat_url},
        {'image': 'img/categories/chargers.webp', 'label_en': 'Fast Chargers', 'label_ar': 'شاحن سريع', 'query': 'charger', 'url': f"{mobile_cat_url}?subcategory=chargers-gan"},
        {'image': 'img/categories/headphones.webp', 'label_en': 'Headphones & Audio', 'label_ar': 'سماعات', 'query': 'headphone', 'url': f"{comp_cat_url}?subcategory=headsets"},
        {'image': 'img/categories/cables.webp', 'label_en': 'Type-C Cables', 'label_ar': 'كابل تايب سي', 'query': 'usb-c', 'url': f"{mobile_cat_url}?subcategory=cables-adapters"},
        {'image': 'img/categories/mouse.webp', 'label_en': 'Wireless Mouse', 'label_ar': 'ماوس لاسلكي', 'query': 'mouse', 'url': f"{comp_cat_url}?subcategory=mice"},
        {'image': 'img/categories/routers.webp', 'label_en': 'Wi-Fi Routers', 'label_ar': 'راوترات', 'query': 'router', 'url': net_cat_url},
        {'image': 'img/categories/stands.webp', 'label_en': 'Gimbals & Mics', 'label_ar': 'جيمبال ومايكات', 'query': 'dji', 'url': f"{mobile_cat_url}?subcategory=content-creation"},
        {'image': 'img/categories/earbuds.webp', 'label_en': 'Wireless Earbuds', 'label_ar': 'ايربودز', 'query': 'earbuds', 'url': f"{mobile_cat_url}?subcategory=wireless-mics-audio"},
        {'image': 'img/categories/tablets.webp', 'label_en': 'Drawing Tablets', 'label_ar': 'تابلت رسم', 'query': 'huion', 'url': graphic_cat_url},
    ]

    categories = Category.objects.prefetch_related('subcategories').all()
    brands = list(Brand.objects.filter(products__available=True).distinct()[:16])
    if len(brands) < 8:
        existing_ids = {b.id for b in brands}
        additional = list(Brand.objects.exclude(id__in=existing_ids)[:16 - len(brands)])
        brands.extend(additional)

    total_catalog_count = Product.objects.filter(available=True).count()

    wishlisted_product_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        wishlisted_product_ids = list(
            Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        )

    return render(request, 'shop/home.html', {
        'banners': banners,
        'featured_products': featured_products,
        'power_products': power_products,
        'bag_products': bag_products,
        'desk_products': desk_products,
        'network_products': network_products,
        'catalog_tabs': catalog_tabs,
        'quick_searches': quick_searches,
        'categories': categories,
        'brands': brands,
        'total_catalog_count': total_catalog_count,
        'wishlisted_product_ids': wishlisted_product_ids,
    })


def about(request):
    """Render the ultra-premium About Us page with SVG animations."""
    return render(request, 'shop/about.html')


from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.utils import timezone

def product_list(request, category_slug=None):
    """List products, optionally filtered by category, subcategory, and GET parameters."""
    category = None
    categories = Category.objects.prefetch_related('subcategories', 'brands').all()
    from django.db.models import Avg, Case, DecimalField, F, IntegerField, Sum, When
    now = timezone.now()
    effective_price_expr = Case(
        When(
            sale_price__isnull=False,
            sale_start__lte=now,
            sale_end__gte=now,
            then=F('sale_price'),
        ),
        default=F('price'),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    products = (
        Product.objects.filter(available=True)
        .select_related('category', 'subcategory', 'brand')
        .annotate(avg_rating=Avg('reviews__rating'), effective_price=effective_price_expr)
    )

    CATEGORY_ALIASES = {
        'apple': 'APPLE',
        'ipad': 'APPLE',
        'ipad-devices': 'APPLE',
        'bags': 'bags',
        'laptop-bags': 'bags',
        'backpacks': 'bags',
        'sleeves': 'bags',
        'computer-accessories': 'Computer-accessories',
        'computer': 'Computer-accessories',
        'pc-accessories': 'Computer-accessories',
        'mobile-accessories': 'mobile-accessories',
        'mobile': 'mobile-accessories',
        'chargers': 'mobile-accessories',
        'network': 'Network',
        'routers': 'Network',
        'router': 'Network',
        'wifi': 'Network',
        'graphic-tablet': 'graphic-tablet',
        'tablets': 'graphic-tablet',
        'tablet': 'graphic-tablet',
        'drawing-tablet': 'graphic-tablet',
    }

    target_cat = (category_slug or request.GET.get('category', '')).strip()
    if target_cat:
        mapped_slug = CATEGORY_ALIASES.get(target_cat.lower(), target_cat)
        if mapped_slug.isdigit():
            category = Category.objects.filter(id=int(mapped_slug)).first()
        else:
            category = (
                Category.objects.filter(slug__iexact=mapped_slug).first()
                or Category.objects.filter(slug__icontains=mapped_slug).first()
                or Category.objects.filter(name__icontains=mapped_slug).first()
            )
        if category:
            products = products.filter(category=category)

    # Subcategory Filter (supports comma-separated multi-subcategory slugs e.g. ?subcategory=mice,keyboards)
    selected_subcategory = request.GET.get('subcategory', '').strip()
    selected_subcategories = [s.strip() for s in selected_subcategory.split(',') if s.strip()]
    active_subcategory_obj = None
    if selected_subcategories and not category:
        from .models import SubCategory
        first_sub = SubCategory.objects.filter(slug__in=selected_subcategories).select_related('category').first()
        if first_sub:
            category = first_sub.category
            products = products.filter(category=category)
    if len(selected_subcategories) == 1:
        from .models import SubCategory
        sub_qs = SubCategory.objects.filter(slug=selected_subcategories[0])
        if category:
            sub_qs = sub_qs.filter(category=category)
        active_subcategory_obj = sub_qs.first()

    # 1. Search Query (smart hybrid search)
    query = request.GET.get('q', '').strip()
    search_scope_expanded = False
    if query:
        from .search import search as smart_search
        result = smart_search(
            query,
            category=category,
            subcategory_slug=selected_subcategories[0] if len(selected_subcategories) == 1 else None
        )
        if result.scope_expanded:
            # Re-base queryset on the whole store (dropping initial category filter)
            products = (
                Product.objects.filter(available=True)
                .select_related('category', 'subcategory', 'brand')
                .annotate(avg_rating=Avg('reviews__rating'), effective_price=effective_price_expr)
            )
            search_scope_expanded = True
        products = products.filter(id__in=result.ids)
        relevance_order = result.ids
    else:
        relevance_order = None

    # 2. Subcategory Filter
    if selected_subcategories and not search_scope_expanded:
        products = products.filter(subcategory__slug__in=selected_subcategories)

    # 3. Brands List (Multi-select - ignore empty values)
    selected_brands = [b for b in request.GET.getlist('brand') if b and b.strip()]
    if selected_brands:
        products = products.filter(brand__slug__in=selected_brands)

    # 3. Price Range (with secure validation)
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    if min_price:
        try:
            products = products.filter(effective_price__gte=Decimal(min_price))
        except (ValueError, InvalidOperation):
            pass

    if max_price:
        try:
            products = products.filter(effective_price__lte=Decimal(max_price))
        except (ValueError, InvalidOperation):
            pass

    # 4. Flags (On Sale, In Stock)
    if request.GET.get('on_sale') == 'true':
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
        products = products.order_by('effective_price')
    elif sort_by == 'price_desc':
        products = products.order_by('-effective_price')
    elif sort_by == 'newest':
        products = products.order_by('-created')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating', '-created')
    elif relevance_order:
        preserved = Case(
            *[When(id=pid, then=pos) for pos, pid in enumerate(relevance_order)],
            output_field=IntegerField()
        )
        products = products.order_by(preserved)
    else:
        products = products.order_by('-id') # Default ordering

    from .models import Brand
    brands_qs = Brand.objects.filter(products__available=True)
    if category:
        brands_qs = brands_qs.filter(products__category=category)
    if selected_subcategories and not search_scope_expanded:
        brands_qs = brands_qs.filter(products__subcategory__slug__in=selected_subcategories)
    brands = brands_qs.distinct().order_by('name')

    # Calculate total quantity of items currently in stock without review JOIN inflation
    total_stock_count = (
        Product.objects.filter(id__in=products.values('id'), stock_quantity__gt=0)
        .aggregate(total=Sum('stock_quantity'))['total']
        or 0
    )

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
        'selected_subcategory': selected_subcategory,
        'selected_subcategories': selected_subcategories,
        'active_subcategory_obj': active_subcategory_obj,
        'wishlisted_product_ids': wishlisted_product_ids,
        'total_stock_count': total_stock_count,
        'search_query': query,
        'search_scope_expanded': search_scope_expanded,
    })


def product_detail(request, id, slug):
    """Display a single product with add-to-cart form."""
    product = get_object_or_404(
        Product.objects.select_related('category', 'subcategory', 'brand').prefetch_related('images'),
        id=id, available=True
    )
    if product.slug != slug:
        return redirect('shop:product_detail', id=product.id, slug=product.slug, permanent=True)
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

    # Verified buyers (exclude cancelled orders)
    from orders.models import OrderItem
    verified_user_ids = set(
        OrderItem.objects.filter(product=product, order__user__isnull=False)
        .exclude(order__status='cancelled')
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
    from django.urls import reverse
    from django.utils.http import url_has_allowed_host_and_scheme

    referer = request.META.get('HTTP_REFERER', '')
    safe_referer = (
        referer
        if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()})
        else reverse('shop:product_list')
    )

    if not request.user.is_authenticated:
        login_redirect = f"{reverse('shop:login')}?next={safe_referer}"
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = login_redirect
            return response
        return redirect(login_redirect)

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

    return redirect(safe_referer)


def search_autocomplete(request):
    """HTMX view for fast local live search dropdown auto-suggest (no external API calls)."""
    query = request.GET.get('q', '').strip()
    products = []
    if len(query) >= 2:
        from django.db.models import Case, When, IntegerField
        from .search.engine import _load_index
        from .search.keyword import keyword_rank

        index = _load_index()
        ranked = keyword_rank(query, index)[:5]
        matched_ids = [pid for pid, _score in ranked]

        if matched_ids:
            preserved = Case(
                *[When(id=pid, then=pos) for pos, pid in enumerate(matched_ids)],
                output_field=IntegerField()
            )
            products = Product.objects.filter(
                id__in=matched_ids,
                available=True
            ).select_related('category', 'brand').order_by(preserved)
        else:
            products = (
                Product.objects.filter(available=True)
                .filter(Q(name__icontains=query) | Q(brand__name__icontains=query))
                .select_related('category', 'brand')[:5]
            )
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
import re

def extract_numeric_spec_score(name, value, existing_numeric=None):
    if existing_numeric and float(existing_numeric) > 0:
        return float(existing_numeric)
    if not value:
        return 0.0
    val_lower = str(value).lower()
    
    # 1. Check direct numbers (e.g. 18 GB, 16GB, 8GB, 14.2 Inch, 120Hz, 8+ Hours)
    match = re.search(r'(\d+(?:\.\d+)?)', val_lower)
    if match:
        num = float(match.group(1))
        if 'ram' in name.lower() or 'gb' in val_lower:
            return num
        if 'tb' in val_lower:
            return num * 1024
        if 'core' in val_lower or 'نواة' in val_lower:
            return num * 8
        if 'hz' in val_lower:
            return num
        if num > 0 and num < 5000:
            return num
            
    # 2. Benchmark qualitative keywords
    score = 50.0
    if any(k in val_lower for k in ['m3', 'm2 pro', 'i9', 'ryzen 9', 'rtx 40', 'retina', 'oled', '4k', 'liquid retina']):
        score = 95.0
    elif any(k in val_lower for k in ['m2', 'm1', 'i7', 'ryzen 7', 'rtx 30', 'qhd', '2k', '144hz']):
        score = 80.0
    elif any(k in val_lower for k in ['i5', 'ryzen 5', 'rtx 20', 'gtx 16', 'fhd', '1080p', 'ips']):
        score = 65.0
    elif any(k in val_lower for k in ['i3', 'ryzen 3', 'celeron', 'hd']):
        score = 45.0
    return score

def _format_currency(amount):
    from django.utils.translation import get_language
    currency = 'ج.م' if (get_language() or '').startswith('ar') else 'EGP'
    return f"{amount:,.2f} {currency}"


def _check_ai_rate_limit(request, scope: str, limit: int = 15, window: int = 60) -> bool:
    from django.core.cache import cache
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', 'unknown')
    key = f"ai_rl:{scope}:{ip}"
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, timeout=window)
        return True
    if count >= limit:
        return False
    try:
        cache.incr(key)
    except Exception:
        cache.set(key, count + 1, timeout=window)
    return True


def serialize_product_battle(product):
    if not product:
        return None
    specs_data = []
    for spec in product.specs.all():
        num_val = extract_numeric_spec_score(spec.name, spec.value, spec.numeric_value)
        specs_data.append({
            'name': spec.name,
            'value': spec.value,
            'numeric_value': num_val,
            'unit': spec.unit or '',
            'icon': spec.icon or '⚡',
        })
    image_url = product.image.url if product.image else ''
    return {
        'id': product.id,
        'name': product.name,
        'image': image_url,
        'price': str(product.current_price),
        'formatted_price': _format_currency(product.current_price),
        'rating': product.average_rating,
        'url': product.get_absolute_url(),
        'specs': specs_data,
    }


def product_battle(request):
    """
    Display the interactive Product Battle Arena page.
    Strictly restricts comparisons to products within the same selected category.
    """
    from django.core.cache import cache
    from django.db.models import Count
    from .models import Category

    # Get all categories with available products (multi-product categories first)
    categories = (
        Category.objects.filter(products__available=True)
        .annotate(available_count=Count('products', filter=Q(products__available=True)))
        .order_by('-available_count', 'name')
    )

    cat_id = request.GET.get('category')
    selected_category = None
    if cat_id and str(cat_id).isdigit():
        selected_category = categories.filter(id=int(cat_id)).first()
    if not selected_category and categories.exists():
        selected_category = categories.first()

    category_products = Product.objects.filter(category=selected_category, available=True).select_related('category', 'brand').order_by('name') if selected_category else Product.objects.none()

    product_a_id = request.GET.get('a')
    product_b_id = request.GET.get('b')

    product_a = category_products.filter(id=int(product_a_id)).prefetch_related('specs').first() if product_a_id and str(product_a_id).isdigit() else None
    product_b = category_products.filter(id=int(product_b_id)).prefetch_related('specs').first() if product_b_id and str(product_b_id).isdigit() else None

    # Defaults if none selected within category
    if not product_a and category_products.exists():
        product_a = category_products.first()
    if not product_b and category_products.count() > 1:
        product_b = category_products[1]
    elif not product_b and category_products.exists():
        product_b = category_products.first()

    # Load cached verdict only (non-blocking); live AI verdict is fetched asynchronously by battle.html
    initial_verdict = None
    if product_a and product_b and product_a.id != product_b.id:
        initial_verdict = cache.get(f"battle:duel:v1:{product_a.id}:{product_b.id}")

    return render(request, 'shop/battle.html', {
        'categories': categories,
        'selected_category': selected_category,
        'products': category_products,
        'product_a': product_a,
        'product_b': product_b,
        'product_a_json': json.dumps(serialize_product_battle(product_a)),
        'product_b_json': json.dumps(serialize_product_battle(product_b)),
        'ai_verdict_json': json.dumps(initial_verdict),
    })


def battle_specs_api(request, product_id):
    """Return JSON spec data for a single product to power live HTMX/Alpine battle updates."""
    product = get_object_or_404(Product.objects.prefetch_related('specs'), id=product_id, available=True)
    return JsonResponse(serialize_product_battle(product))


def battle_ai_verdict(request):
    """
    API endpoint that accepts product_a_id and product_b_id (via POST or GET) and returns AI Referee Verdict.
    """
    from .ai_service import evaluate_product_duel

    if not _check_ai_rate_limit(request, 'battle_verdict', limit=20, window=60):
        return JsonResponse({'error': 'Too many AI requests. Please wait a moment.'}, status=429)

    try:
        if request.method == 'POST':
            try:
                data = json.loads(request.body.decode('utf-8'))
                raw_a = data.get('product_a_id', 0)
                raw_b = data.get('product_b_id', 0)
            except Exception:
                raw_a = request.POST.get('product_a_id', 0)
                raw_b = request.POST.get('product_b_id', 0)
        else:
            raw_a = request.GET.get('product_a_id') or request.GET.get('a') or 0
            raw_b = request.GET.get('product_b_id') or request.GET.get('b') or 0

        prod_a_id = int(raw_a)
        prod_b_id = int(raw_b)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid product IDs'}, status=400)

    if prod_a_id <= 0 or prod_b_id <= 0:
        return JsonResponse({'error': 'Both product_a_id and product_b_id are required'}, status=400)

    res = evaluate_product_duel(prod_a_id, prod_b_id)
    if not res.get('success'):
        return JsonResponse({'error': res.get('error', 'Could not evaluate duel')}, status=400)

    return JsonResponse(res)


@require_POST
def tech_finder_chat(request):
    """
    Handle natural language queries for AI Tech Finder and return matched product JSON payload.
    """
    from .ai_service import ask_ai_tech_finder

    if not _check_ai_rate_limit(request, 'tech_finder', limit=15, window=60):
        return JsonResponse({'error': 'Too many AI requests. Please wait a moment.'}, status=429)

    try:
        data = json.loads(request.body.decode('utf-8'))
        prompt = data.get('prompt', '').strip()
    except Exception:
        prompt = request.POST.get('prompt', '').strip()

    if not prompt:
        return JsonResponse({'error': 'Prompt is required'}, status=400)

    ai_result = ask_ai_tech_finder(prompt)
    if not ai_result.get('success'):
        return JsonResponse({'error': ai_result.get('error', 'Could not find a match')}, status=400)

    rec_data = ai_result['data']
    product_ids = rec_data.get('product_ids', [])
    if not product_ids and rec_data.get('product_id'):
        product_ids = [rec_data['product_id']]

    db_products = {p.id: p for p in Product.objects.filter(id__in=product_ids, available=True).select_related('category', 'brand').prefetch_related('specs')}

    products_list = []
    for pid in product_ids:
        if pid in db_products:
            p = db_products[pid]
            specs_list = [{'name': s.name, 'value': s.value, 'icon': s.icon} for s in p.specs.all()[:3]]
            products_list.append({
                'id': p.id,
                'name': p.name,
                'image': p.image.url if p.image else '',
                'price': float(p.current_price),
                'formatted_price': _format_currency(p.current_price),
                'is_on_sale': p.is_on_sale,
                'original_price': _format_currency(p.price) if p.is_on_sale else None,
                'url': p.get_absolute_url(),
                'brand': p.brand.name if p.brand else '',
                'specs': specs_list
            })

    return JsonResponse({
        'success': True,
        'product': products_list[0] if products_list else None,
        'products': products_list,
        'is_multi': len(products_list) > 1,
        'match_score': rec_data.get('match_score', 95) if products_list else 0,
        'ai_message': rec_data.get('ai_message', 'للأسف مفيش منتج متطابق مع طلبك متاح حالياً.'),
        'highlights': rec_data.get('highlights', []),
        'is_ai': ai_result.get('is_ai', False)
    })

