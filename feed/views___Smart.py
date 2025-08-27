# feed/views.py

from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib import messages
from feed.models import Post, Advertisement
from feed.utils_ads import track_ad_click
from feed.utils_posts import\
    get_smart_posts_queryset, \
    mix_smart_posts_with_ads, \
    get_post_targeting_stats

from accounts.utils import get_user_from_jwt
import json
import logging

logger = logging.getLogger(__name__)


def public_posts(request):
    """Main public posts page with smart post filtering and integrated advertisements"""
    jwt_user = get_user_from_jwt(request)
    logger.info(f"Public posts request from user: {jwt_user}")

    # Get smart posts based on user interests
    if jwt_user:
        posts = get_smart_posts_queryset(jwt_user, fallback_limit=0.3)

        # Get targeting stats for debugging/analytics
        targeting_stats = get_post_targeting_stats(jwt_user)
        logger.info(f"Post targeting stats: {targeting_stats}")
    else:
        posts = Post.objects.none()

    total_posts = posts.count()
    logger.info(f"Total smart posts available: {total_posts}")

    # Get first page of smart posts
    paginator = Paginator(posts, 10)
    first_page = paginator.get_page(1)

    # Mix smart posts with advertisements
    mixed_items = mix_smart_posts_with_ads(
        first_page, jwt_user, posts_per_page=10, ads_frequency=10)

    context = {
        'items': mixed_items,
        'total_posts': total_posts,
        'jwt_user': jwt_user,
        'has_next': first_page.has_next(),
        'next_page_number': 2 if first_page.has_next() else None,
        # Optional: for frontend display
        'targeting_stats': targeting_stats if jwt_user else None,
    }

    return render(request, 'public-posts.html', context)


def load_more_posts(request):
    """AJAX endpoint for loading more smart posts with ads"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    jwt_user = get_user_from_jwt(request)
    page_number = request.GET.get('page', 1)

    logger.info(f"Load more smart posts: user={jwt_user}, page={page_number}")

    # Get smart posts based on user interests
    if jwt_user:
        posts = get_smart_posts_queryset(jwt_user, fallback_limit=0.3)
    else:
        posts = Post.objects.none()

    paginator = Paginator(posts, 10)
    page = paginator.get_page(page_number)

    # Mix smart posts with advertisements
    mixed_items = mix_smart_posts_with_ads(
        page, jwt_user, posts_per_page=10, ads_frequency=10)

    # Render mixed content HTML
    posts_html = render_to_string('components/posts_list.html', {
        'items': mixed_items,
        'jwt_user': jwt_user
    })

    return JsonResponse({
        'html': posts_html,
        'has_next': page.has_next(),
        'next_page': page.next_page_number() if page.has_next() else None,
        'current_page': page.number,
        'total_pages': paginator.num_pages
    })


def my_posts(request):
    """Main user posts page - shows user's own posts, no smart filtering needed"""
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

    # Get first page of posts WITHOUT ads (user's own posts)
    paginator = Paginator(user_posts, 10)
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
    """AJAX endpoint for loading more user posts with ads"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    jwt_user = get_user_from_jwt(request)

    if not jwt_user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    page_number = request.GET.get('page', 1)

    user_posts = Post.objects.select_related('author').filter(
        author=jwt_user
    ).order_by('-created_at')

    paginator = Paginator(user_posts, 10)
    page = paginator.get_page(page_number)

    # Mix user posts with advertisements (different frequency)
    mixed_items = mix_smart_posts_with_ads(
        page, jwt_user, posts_per_page=10, ads_frequency=15)

    # Render mixed content HTML
    posts_html = render_to_string('components/posts_list.html', {
        'items': mixed_items,
        'jwt_user': jwt_user
    })

    return JsonResponse({
        'html': posts_html,
        'has_next': page.has_next(),
        'next_page': page.next_page_number() if page.has_next() else None,
        'current_page': page.number,
        'total_pages': paginator.num_pages
    })


def track_ad_click_view(request):
    """API endpoint for tracking advertisement clicks"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        ad_id = data.get('ad_id')

        if not ad_id:
            return JsonResponse({'error': 'Missing ad_id'}, status=400)

        success = track_ad_click(ad_id)

        if success:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Ad not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in track_ad_click_view: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def debug_targeting_view(request):
    """Debug endpoint to see how post targeting works for current user"""
    jwt_user = get_user_from_jwt(request)

    if not jwt_user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from feed.utils_posts import debug_user_post_matching, get_post_targeting_stats

    # Get targeting stats
    stats = get_post_targeting_stats(jwt_user)

    # Get debug info for recent posts
    debug_info = debug_user_post_matching(jwt_user, limit=10)

    return JsonResponse({
        'user_id': jwt_user.id,
        'username': jwt_user.username,
        'targeting_stats': stats,
        'post_matching_debug': debug_info
    }, indent=2)  # Pretty print for debugging
