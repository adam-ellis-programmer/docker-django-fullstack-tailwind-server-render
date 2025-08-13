from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from accounts.utils import get_user_from_jwt


def home(request):
    # if logged in show dashboard
    user = get_user_from_jwt(request)
    if user:
        print('------user------') 
        print(user)
        return redirect('accounts:profile_page')
    """Home page view"""
    return render(request, 'core/home.html')


def about(request):
    """About page view"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact page view"""
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Here you would normally process the form data
        # (save to database, send email, etc.)

        # For now, just show a success message
        messages.success(
            request, f'Thank you {name}! Your message has been received.')

    return render(request, 'core/contact.html')
