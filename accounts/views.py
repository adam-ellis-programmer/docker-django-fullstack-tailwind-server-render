import json
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.middleware.csrf import get_token
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .utils import create_jwt_response, get_user_from_jwt

User = get_user_model()


@ensure_csrf_cookie
def signup_page(request):
    """Render signup page"""
    return render(request, 'accounts/signup.html')


@ensure_csrf_cookie
def signin_page(request):
    """Render signin page"""
    return render(request, 'accounts/signin.html')


@csrf_exempt
@require_http_methods(["POST"])
def signup_api(request):
    """Handle user registration"""
    try:
        data = json.loads(request.body)

        # Extract data
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()

        # Basic validation
        if not email or not username or not password:
            return JsonResponse({
                'success': False,
                'message': 'Email, username, and password are required'
            }, status=400)

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'User with this email already exists'
            }, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already taken'
            }, status=400)

        # Create user
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Return JWT cookie response
        return create_jwt_response(user, "Account created successfully!")

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"Signup error: {e}")  # For debugging
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during registration'
        }, status=500)


@require_http_methods(["POST"])
def signin_api(request):
    """Handle user login - CSRF protected"""
    try:
        data = json.loads(request.body)

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return JsonResponse({
                'success': False,
                'message': 'Email and password are required'
            }, status=400)

        # Authenticate user
        user = authenticate(request, username=email, password=password)

        if user is None:
            return JsonResponse({
                'success': False,
                'message': 'Invalid email or password'
            }, status=401)

        if not user.is_active:
            return JsonResponse({
                'success': False,
                'message': 'Account is disabled'
            }, status=401)

        # 🎯 CRITICAL: Return user data in the response for immediate UI update
        response_data = {
            'success': True,
            'message': 'Logged in successfully!',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'age': user.age if hasattr(user, 'age') else None,
                'bio': user.bio if hasattr(user, 'bio') else '',
                'is_email_verified': user.is_email_verified if hasattr(user, 'is_email_verified') else False,
                'date_joined': user.date_joined.isoformat()
            }
        }

        # Create JWT response with user data
        jwt_response = create_jwt_response(user, "Logged in successfully!")

        # Parse the JWT response to get the JSON data
        jwt_data = json.loads(jwt_response.content.decode())

        # Create a new response with our enhanced data but preserve the JWT cookie
        response = JsonResponse(response_data)

        # Copy the auth_token cookie from the JWT response
        if 'auth_token' in jwt_response.cookies:
            response.set_cookie(
                'auth_token',
                jwt_response.cookies['auth_token'].value,
                max_age=jwt_response.cookies['auth_token']['max-age'],
                httponly=jwt_response.cookies['auth_token']['httponly'],
                secure=jwt_response.cookies['auth_token']['secure'],
                samesite=jwt_response.cookies['auth_token']['samesite']
            )

        return response

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"Signin error: {e}")  # For debugging
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during login'
        }, status=500)


@require_http_methods(["POST"])
def signout_api(request):
    """Handle user logout"""
    response = JsonResponse({
        'success': True,
        'message': 'Logged out successfully'
    })

    # Clear the auth cookie
    response.delete_cookie('auth_token')
    return response


@ensure_csrf_cookie
def profile_page(request):
    """Render user profile/dashboard page with context data"""
    # Get user from JWT token
    user = get_user_from_jwt(request)

    # If no user found, redirect to signin page
    if not user:
        return redirect('accounts:signin_page')

    # Calculate member duration
    now = datetime.now()
    join_date = user.date_joined.replace(
        tzinfo=None) if user.date_joined.tzinfo else user.date_joined
    duration = relativedelta(now, join_date)

    # Format member since text
    if duration.years > 0:
        member_since = f"{duration.years} year{'s' if duration.years != 1 else ''}"
    elif duration.months > 0:
        member_since = f"{duration.months} month{'s' if duration.months != 1 else ''}"
    elif duration.days > 0:
        member_since = f"{duration.days} day{'s' if duration.days != 1 else ''}"
    else:
        member_since = "Today"

    # Get user initials
    if user.first_name and user.last_name:
        initials = (user.first_name[0] + user.last_name[0]).upper()
    elif user.username:
        initials = user.username[:2].upper()
    else:
        initials = "U"

    # Prepare context data
    context = {
        'user': user,
        'user_data': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name or 'Not provided',
            'last_name': user.last_name or 'Not provided',
            'full_name': user.get_full_name() or user.username,
            'initials': initials,
            'age': getattr(user, 'age', None) or 'N/A',
            'bio': getattr(user, 'bio', '') or 'No bio provided yet.',
            'is_email_verified': getattr(user, 'is_email_verified', False),
            'email_status': 'Verified' if getattr(user, 'is_email_verified', False) else 'Pending',
            'date_joined': user.date_joined,
            'date_joined_formatted': user.date_joined.strftime('%B %d, %Y'),
            'member_since': member_since,
        }
    }

    return render(request, 'accounts/profile.html', context)


@require_http_methods(["GET"])
def profile_api(request):
    """Get current user profile (protected route example)"""
    user = get_user_from_jwt(request)

    if not user:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)

    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'age': user.age if hasattr(user, 'age') else None,
            'bio': user.bio if hasattr(user, 'bio') else '',
            'is_email_verified': user.is_email_verified if hasattr(user, 'is_email_verified') else False,
            'date_joined': user.date_joined.isoformat()
        }
    })


@require_http_methods(["GET"])
def auth_status_api(request):
    """Check if user is authenticated and return user data"""
    # how does this have access to the request and also
    # find the id to get the user
    user = get_user_from_jwt(request)

    if not user:
        return JsonResponse({
            'authenticated': False,
            'user': None
        })

    return JsonResponse({
        'authenticated': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'age': user.age if hasattr(user, 'age') else None,
            'bio': user.bio if hasattr(user, 'bio') else '',
            'is_email_verified': user.is_email_verified if hasattr(user, 'is_email_verified') else False,
            'date_joined': user.date_joined.isoformat()
        }
    })
