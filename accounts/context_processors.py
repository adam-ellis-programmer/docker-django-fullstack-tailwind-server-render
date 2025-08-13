# accounts/context_processors.py
"""
Context processor to add JWT user authentication status to all templates
"""
from .utils import get_user_from_jwt


def jwt_auth_context(request):
    """
    Add JWT authentication context to all templates.
    This makes user data available in every template without API calls.
    """
    user = get_user_from_jwt(request)

    if user:
        return {
            'jwt_authenticated': True,
            'test': False,
            'jwt_user': user,
            'jwt_user_data': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'full_name': user.get_full_name() or user.username,
                'is_email_verified': getattr(user, 'is_email_verified', False),
            }
        }

    return {  # ← Still Available in ALL templates
        'jwt_authenticated': False,
        'jwt_user': None,
        'jwt_user_data': None
    }
