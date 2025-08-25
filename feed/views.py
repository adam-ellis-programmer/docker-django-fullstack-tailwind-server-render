from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from feed.models import Post
from accounts.utils import get_user_from_jwt
from django.contrib import messages
from pprint import pprint

# ===============================================================================
# PUBLIC POSTS WITH INFINITE SCROLL
# ===============================================================================


def public_posts(request):
    """Main public posts page"""
    jwt_user = get_user_from_jwt(request)

    if jwt_user:
        posts = Post.objects.select_related('author').order_by('-created_at')
    else:
        posts = Post.objects.none()

    # Get first page of posts (3 posts per page for testing)
    paginator = Paginator(posts, 3)  # Changed from 12 to 3
    first_page = paginator.get_page(1)

    context = {
        'posts': first_page,
        'total_posts': posts.count(),
        'jwt_user': jwt_user,
        'has_next': first_page.has_next(),
        'next_page_number': 2 if first_page.has_next() else None,
    }

    return render(request, 'public-posts.html', context)


def load_more_posts(request):
    """AJAX endpoint for loading more posts"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    jwt_user = get_user_from_jwt(request)
    page_number = request.GET.get('page', 1)

    if jwt_user:
        posts = Post.objects.select_related('author').order_by('-created_at')
    else:
        posts = Post.objects.none()

    # The Paginator uses SQL LIMIT and OFFSET:
    paginator = Paginator(posts, 3)  # Changed from 12 to 3
    page = paginator.get_page(page_number)

    # Render posts HTML
    posts_html = render_to_string('components/posts_list.html', {
        'posts': page,  # This contains exactly 3 Post objects
        'jwt_user': jwt_user  # This is actual User object
    })

    return JsonResponse({
        'html': posts_html,
        'has_next': page.has_next(),
        'next_page': page.next_page_number() if page.has_next() else None,
        'current_page': page.number,
        'total_pages': paginator.num_pages
    })


def my_posts(request):
    """Main user posts page"""
    jwt_user = get_user_from_jwt(request)

    if not jwt_user:
        messages.error(request, 'Please log in to view your posts.')
        return redirect('signin')

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

    # Handle None values for averages
    stats['avg_likes'] = round(stats['avg_likes'] or 0, 1)
    stats['avg_comments'] = round(stats['avg_comments'] or 0, 1)

    # Get first page of posts (3 posts per page for testing)
    paginator = Paginator(user_posts, 3)  # Changed from 12 to 3
    first_page = paginator.get_page(1)

    # Get recent activity (last 5 posts)
    recent_posts = user_posts[:5]

    # Calculate engagement rate
    total_engagement = (stats['total_likes'] or 0) + \
        (stats['total_comments'] or 0) + (stats['total_shares'] or 0)
    engagement_rate = round(total_engagement / max(stats['total_posts'], 1), 1)

    context = {
        'jwt_user': jwt_user,
        'posts': first_page,
        'stats': stats,
        'recent_posts': recent_posts,
        'engagement_rate': engagement_rate,
        'total_engagement': total_engagement,
        'has_next': first_page.has_next(),
        'next_page_number': 2 if first_page.has_next() else None,
    }

    return render(request, 'user-posts.html', context)


def load_more_user_posts(request):
    """AJAX endpoint for loading more user posts"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    jwt_user = get_user_from_jwt(request)

    if not jwt_user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    page_number = request.GET.get('page', 1)

    user_posts = Post.objects.select_related('author').filter(
        author=jwt_user
    ).order_by('-created_at')

    paginator = Paginator(user_posts, 3)  # Changed from 12 to 3
    page = paginator.get_page(page_number)

    # Render posts HTML
    posts_html = render_to_string('components/posts_list.html', {
        'posts': page,
        'jwt_user': jwt_user
    })

    return JsonResponse({
        'html': posts_html,
        'has_next': page.has_next(),
        'next_page': page.next_page_number() if page.has_next() else None,
        'current_page': page.number,
        'total_pages': paginator.num_pages
    })
