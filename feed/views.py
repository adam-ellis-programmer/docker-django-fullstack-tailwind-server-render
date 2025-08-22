

from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Avg
from feed.models import Post
from accounts.utils import get_user_from_jwt
from django.contrib import messages

from pprint import pprint
'''
from django.db.models import Q
posts = Post.objects.filter(
    Q(is_public=True) | Q(author=jwt_user)  # | means OR
).order_by('-created_at')
'''

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


# ===============================================================================
#  PUBLIC POSTS
# ===============================================================================

def public_posts(request):
    # Get user from JWT token
    jwt_user = get_user_from_jwt(request)

    # Filter posts based on JWT user
    if jwt_user:
        # Get posts only by the logged-in JWT user
        posts = Post.objects.select_related('author').order_by('-created_at')
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


# ===============================================================================
# USERS OWN POSTS PAGE
# ===============================================================================

def my_posts(request):
    # Get user from JWT token
    jwt_user = get_user_from_jwt(request)

    # Redirect to login if no JWT user
    if not jwt_user:
        messages.error(request, 'Please log in to view your posts.')
        return redirect('signin')  # Adjust redirect URL as needed

    # Get user's posts
    user_posts = Post.objects.select_related('author').filter(
        author=jwt_user
    ).order_by('-created_at')

    # Calculate user stats
    stats = user_posts.aggregate(
        total_posts=Count('id'),
        total_likes=Sum('likes'),
        total_comments=Sum('comments'),
        total_shares=Sum('shares'),
        avg_likes=Avg('likes'),
        avg_comments=Avg('comments'),
    )

    # Handle None values for averages (when no posts exist)
    stats['avg_likes'] = round(stats['avg_likes'] or 0, 1)
    stats['avg_comments'] = round(stats['avg_comments'] or 0, 1)

    # Get recent activity (last 5 posts)
    recent_posts = user_posts[:5]

    # Calculate engagement rate (likes + comments + shares per post)
    total_engagement = (stats['total_likes'] or 0) + \
        (stats['total_comments'] or 0) + (stats['total_shares'] or 0)
    engagement_rate = round(total_engagement / max(stats['total_posts'], 1), 1)
    # 0 posts → 0 engagement → 0/1 = 0 (correct result)

    context = {
        'jwt_user': jwt_user,
        'posts': user_posts,
        'stats': stats,
        'recent_posts': recent_posts,
        'engagement_rate': engagement_rate,
        'total_engagement': total_engagement,
    }

    return render(request, 'user-posts.html', context)
