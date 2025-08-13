import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse

User = get_user_model()


def generate_jwt_token(user):
    """Generate JWT token for user"""
    now = datetime.now(timezone.utc)

    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': now + timedelta(days=7),  # Token expires in 7 days
        'iat': now  # Issued at
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    return token


def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def get_user_from_jwt(request):
    """Extract user from JWT token in cookies"""
    token = request.COOKIES.get('auth_token')
    if not token:
        return None

    payload = verify_jwt_token(token)
    if not payload:
        return None

    try:
        user = User.objects.get(id=payload['user_id'])
        return user
    except User.DoesNotExist:
        return None


def create_jwt_response(user, message="Success"):
    """Create response with JWT cookie"""
    token = generate_jwt_token(user)

    response = JsonResponse({
        'success': True,
        'message': message,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.get_full_name()
        }
    })

    # Set HTTP-only cookie (secure against XSS)
    response.set_cookie(
        'auth_token',
        token,
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=True,  # Cannot be accessed by JavaScript (XSS protection)
        secure=False,   # Set to True in production (requires HTTPS)
        samesite='Lax'  # CSRF protection
    )

    return response
