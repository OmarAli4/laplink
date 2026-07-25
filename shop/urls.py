from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.product_list, name='product_list'),
    path('catalog/<slug:category_slug>/',
         views.product_list,
         name='product_list_by_category'),
    path('product/<int:id>/<slug:slug>/',
         views.product_detail,
         name='product_detail'),
    path('recommender/<int:product_id>/',
         views.product_recommender,
         name='product_recommender'),
    path('about/', views.about, name='about'),
    
    # Auth
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    
    # Wishlist
    path('wishlist/', views.wishlist_detail, name='wishlist_detail'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),

    # Search Live Autocomplete
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),

    # Product Battle / Duel Arena
    path('battle/', views.product_battle, name='product_battle'),
    path('battle/specs/<int:product_id>/', views.battle_specs_api, name='battle_specs_api'),

    # Preview 404
    path('preview-404/', views.preview_404, name='preview_404'),
]

