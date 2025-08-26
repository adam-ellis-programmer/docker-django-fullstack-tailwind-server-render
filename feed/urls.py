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
    
    # Ad tracking
    path('api/track-ad-click/', views.track_ad_click, name='track_ad_click'),
]