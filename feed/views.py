from django.shortcuts import render
from feed.models import Post
from accounts.utils import get_user_from_jwt  # Import your JWT utility
from pprint import pprint


'''
from django.db.models import Q
posts = Post.objects.filter(
    Q(is_public=True) | Q(author=jwt_user)  # | means OR
).order_by('-created_at')
'''


def public_posts(request):
    # Get user from JWT token
    jwt_user = get_user_from_jwt(request)

    # print('--- JWT USER DEBUG ---')
    # if jwt_user:
    #     print(f'JWT User: {jwt_user}')
    #     print(f'User ID: {jwt_user.id}')
    #     print(f'Username: {jwt_user.username}')
    #     print(f'Email: {jwt_user.email}')
    #     print(f'Is authenticated: True')
    # else:
    #     print('No JWT user found - user not authenticated')
    # print('--- END JWT USER DEBUG ---')

    # Filter posts based on JWT user
    if jwt_user:
        # Get posts only by the logged-in JWT user
        posts = Post.objects.select_related('author').filter(
            author=jwt_user
        ).order_by('-created_at')
    else:
        # If no JWT user, return empty queryset or redirect to login
        posts = Post.objects.none()  # Empty queryset
        # Or you could redirect: return redirect('signin')

    context = {
        'posts': posts,
        'total_posts': posts.count(),
        'jwt_user': jwt_user  # Pass to template if needed
    }

    return render(request, 'public-posts.html', context)


def my_posts(request):
    return render(request, 'user-posts.html')
