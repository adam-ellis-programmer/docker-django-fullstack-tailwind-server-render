from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    # Page views
    path('posts', views.public_posts, name='public_posts'),
    path('my-posts', views.my_posts, name='my-posts'),
]
