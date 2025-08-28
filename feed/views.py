# feed/views.py
from django.views.decorators.csrf import csrf_exempt
from feed.models import AdImpression, create_ad_impression, update_ad_impression_duration
from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib import messages
from feed.models import Post, Advertisement, PostLike, process_user_interaction
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
    """Main public posts page showing ALL posts with integrated advertisements"""
    jwt_user = get_user_from_jwt(request)
    logger.info(f"Public posts request from user: {jwt_user}")

    # Get ALL posts instead of smart filtering
    posts = Post.objects.select_related('author').order_by('-created_at')

    total_posts = posts.count()
    logger.info(f"Total posts available: {total_posts}")

    # Get first page of posts
    paginator = Paginator(posts, 10)
    first_page = paginator.get_page(1)

    # Mix posts with advertisements
    mixed_items = mix_smart_posts_with_ads(
        first_page, jwt_user, posts_per_page=10, ads_frequency=10)

    # ADD THE CODE HERE - right after mixed_items is created
    # Add user like status to each post
    if jwt_user:
        # Get all post IDs that the user has liked
        user_liked_posts = set(PostLike.objects.filter(
            user=jwt_user
        ).values_list('post_id', flat=True))

        logger.info(f"User {jwt_user.id} has liked posts: {user_liked_posts}")

        # ----- ADDS A FIELD ON THE FLY -- for logged in users to click
        # Add user_has_liked attribute to each item
        for item in mixed_items:
            # mixed_items list contains two different types of objects (post and advert)
            if hasattr(item, 'id') and not hasattr(item, 'type'):  # It's a post, not an ad
                item.user_has_liked = item.id in user_liked_posts
                logger.info(
                    f"Post {item.id} - user_has_liked: {item.user_has_liked}")
            else:
                item.user_has_liked = False
    else:
        logger.info("No JWT user - setting all user_has_liked to False")
        # User not logged in
        for item in mixed_items:
            item.user_has_liked = False

    context = {
        'items': mixed_items,
        'total_posts': total_posts,
        'jwt_user': jwt_user,
        'has_next': first_page.has_next(),
        'next_page_number': 2 if first_page.has_next() else None,
    }

    return render(request, 'public-posts.html', context)


def load_more_posts(request):
    """AJAX endpoint for loading more posts (ALL posts, not filtered)"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    jwt_user = get_user_from_jwt(request)
    page_number = request.GET.get('page', 1)

    logger.info(f"Load more posts: user={jwt_user}, page={page_number}")

    # Get ALL posts instead of smart filtering
    posts = Post.objects.select_related('author').order_by('-created_at')

    paginator = Paginator(posts, 10)
    page = paginator.get_page(page_number)

    # Mix posts with advertisements
    mixed_items = mix_smart_posts_with_ads(
        page, jwt_user, posts_per_page=10, ads_frequency=10)

    # ADD USER LIKE STATUS - Same as in public_posts view
    if jwt_user:
        user_liked_posts = set(PostLike.objects.filter(
            user=jwt_user
        ).values_list('post_id', flat=True))

        for item in mixed_items:
            if hasattr(item, 'id') and not hasattr(item, 'type'):  # It's a post, not an ad
                item.user_has_liked = item.id in user_liked_posts
            else:
                item.user_has_liked = False
    else:
        for item in mixed_items:
            item.user_has_liked = False

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


# ==========================================================================
# TOGGLE LIKE BUTTON
# ==========================================================================

def toggle_like(request):
    """AJAX endpoint to toggle post likes with PostLike tracking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Get user from JWT token
    jwt_user = get_user_from_jwt(request)
    if not jwt_user:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')

        if not post_id:
            return JsonResponse({'error': 'Missing post_id'}, status=400)

        # Get the post
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)

        # Check if user already liked this post
        existing_like = PostLike.objects.filter(
            user=jwt_user, post=post).first()

        if existing_like:
            # User already liked - so unlike it
            existing_like.delete()
            post.likes = max(0, post.likes - 1)  # Prevent negative likes
            post.save()

            # Update user interests (unlike action)
            process_user_interaction(jwt_user, post, 'unlike')

            return JsonResponse({
                'success': True,
                'action': 'unliked',
                'new_like_count': post.likes,
                'user_has_liked': False
            })
        else:
            # User hasn't liked - so like it
            PostLike.objects.create(user=jwt_user, post=post)
            post.likes += 1
            post.save()

            # Update user interests (like action)
            process_user_interaction(jwt_user, post, 'like')

            return JsonResponse({
                'success': True,
                'action': 'liked',
                'new_like_count': post.likes,
                'user_has_liked': True
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in toggle_like: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# ==========================================================================
# AD TRACKING VIEWS
# ==========================================================================

# Add these views to your feed/views.py file


@csrf_exempt
def track_ad_impression(request):
    """API endpoint to track when an ad comes into view"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        ad_id = data.get('ad_id')

        if not ad_id:
            return JsonResponse({'error': 'Missing ad_id'}, status=400)

        # Get the advertisement
        try:
            advertisement = Advertisement.objects.get(id=ad_id)
        except Advertisement.DoesNotExist:
            return JsonResponse({'error': 'Ad not found'}, status=404)

        # Get user from JWT token
        jwt_user = get_user_from_jwt(request)

        # Create ad impression
        impression = create_ad_impression(
            advertisement=advertisement,
            user=jwt_user,
            request=request
        )

        if impression:
            return JsonResponse({
                'success': True,
                'impression_id': impression.id,
                'message': 'Ad impression tracked'
            })
        else:
            # Duplicate impression prevented
            return JsonResponse({
                'success': True,
                'message': 'Duplicate impression prevented'
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in track_ad_impression: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
def update_ad_impression(request):
    """API endpoint to update ad impression with viewing duration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        impression_id = data.get('impression_id')
        duration_seconds = data.get('duration_seconds', 0)
        viewport_percentage = data.get('viewport_percentage', 0)

        if not impression_id:
            return JsonResponse({'error': 'Missing impression_id'}, status=400)

        success = update_ad_impression_duration(
            impression_id=impression_id,
            duration_seconds=duration_seconds,
            viewport_percentage=viewport_percentage
        )

        if success:
            return JsonResponse({
                'success': True,
                'message': 'Ad impression updated'
            })
        else:
            return JsonResponse({'error': 'Failed to update impression'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in update_ad_impression: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def get_ad_analytics(request):
    """API endpoint to get ad analytics data"""
    jwt_user = get_user_from_jwt(request)

    if not jwt_user or not jwt_user.is_staff:  # Only staff can view analytics
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        # Get query parameters
        ad_id = request.GET.get('ad_id')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Base queryset
        impressions = AdImpression.objects.select_related(
            'advertisement', 'user')

        # Filter by ad_id if provided
        if ad_id:
            impressions = impressions.filter(advertisement_id=ad_id)

        # Filter by date range if provided
        if start_date:
            impressions = impressions.filter(impression_start__gte=start_date)
        if end_date:
            impressions = impressions.filter(impression_start__lte=end_date)

        # Calculate analytics
        total_impressions = impressions.count()
        valid_impressions = impressions.filter(
            is_valid_impression=True).count()

        avg_view_duration = impressions.filter(
            view_duration__gt=0
        ).aggregate(avg_duration=Avg('view_duration'))['avg_duration'] or 0

        unique_users = impressions.filter(
            user__isnull=False).values('user').distinct().count()

        # Group by advertisement
        ad_stats = impressions.values('advertisement__id', 'advertisement__brand').annotate(
            impression_count=Count('id'),
            valid_impression_count=Count(
                'id', filter=Q(is_valid_impression=True)),
            avg_duration=Avg('view_duration'),
            unique_user_count=Count('user', distinct=True)
        ).order_by('-impression_count')

        return JsonResponse({
            'summary': {
                'total_impressions': total_impressions,
                'valid_impressions': valid_impressions,
                'avg_view_duration': round(avg_view_duration, 2),
                'unique_users': unique_users,
                'validation_rate': round((valid_impressions / max(total_impressions, 1)) * 100, 1)
            },
            'by_ad': list(ad_stats),
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        })

    except Exception as e:
        logger.error(f"Error in get_ad_analytics: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
