from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Page views
    path('signup/', views.signup_page, name='signup_page'),
    path('signin/', views.signin_page, name='signin_page'),
    path('profile/', views.profile_page, name='profile_page'),

    # API endpoints
    path('api/signup/', views.signup_api, name='signup_api'),
    path('api/signin/', views.signin_api, name='signin_api'),
    path('api/signout/', views.signout_api, name='signout_api'),
    path('api/profile/', views.profile_api, name='profile_api'),
    path('api/auth-status/', views.auth_status_api, name='auth_status_api'),
]
