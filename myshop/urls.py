from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

admin.site.enable_nav_sidebar = True

urlpatterns = [
    path('manage-store/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('anymail/', include('anymail.urls')),
]

urlpatterns += i18n_patterns(
    path('cart/', include('cart.urls', namespace='cart')),
    path('coupons/', include('coupons.urls', namespace='coupons')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('', include('shop.urls', namespace='shop')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'shop.views.custom_404_view'

