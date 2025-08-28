# Updated feed/urls.py
from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    # Page views
    path('posts', views.public_posts, name='public_posts'),
    path('my-posts', views.my_posts, name='my-posts'),

    # AJAX endpoints for infinite scroll
    path('api/load-more-posts/', views.load_more_posts, name='load_more_posts'),
    path('api/load-more-user-posts/', views.load_more_user_posts, name='load_more_user_posts'),

    # Ad tracking endpoints
    path('api/track-ad-click/', views.track_ad_click_view, name='track_ad_click'),
    path('api/track-ad-impression/', views.track_ad_impression, name='track_ad_impression'),
    path('api/update-ad-impression/', views.update_ad_impression, name='update_ad_impression'),
    path('api/ad-analytics/', views.get_ad_analytics, name='ad_analytics'),

    # Toggle Likes on post article
    path('toggle-like/', views.toggle_like, name='toggle_like'),
]