# feed/utils_posts.py

from django.db.models import Q, Case, When, FloatField, Value
from feed.models import Post, UserInterest
import random
import logging

logger = logging.getLogger(__name__)


def shuffle_posts_by_relevance(posts_queryset):
    """
    Shuffle posts while maintaining relevance groupings

    Args:
        posts_queryset: QuerySet with relevance scoring

    Returns:
        List of posts shuffled within relevance groups
    """
    # Convert to list and group by relevance score
    posts_list = list(posts_queryset)

    # Group posts by relevance score
    relevance_groups = {}
    for post in posts_list:
        score = getattr(post, 'relevance_score', 0) or getattr(
            post, 'interest_score', 0)
        if score not in relevance_groups:
            relevance_groups[score] = []
        relevance_groups[score].append(post)

    # Shuffle within each group and combine
    shuffled_posts = []
    for score in sorted(relevance_groups.keys(), reverse=True):  # Highest relevance first
        group_posts = relevance_groups[score]
        random.shuffle(group_posts)  # Shuffle within the relevance group
        shuffled_posts.extend(group_posts)

    return shuffled_posts


def get_smart_posts_queryset(user=None, fallback_limit=0.3, randomize=True):
    """
    Get posts filtered by user interests with smart fallback

    Args:
        user: User object for interest targeting
        fallback_limit: Percentage (0.0-1.0) of non-targeted posts to include

    Returns:
        QuerySet of Post objects ordered by relevance and recency
    """
    base_posts = Post.objects.select_related('author').order_by('-created_at')

    if not user:
        logger.info("No user provided, returning all posts")
        return base_posts

    # Get user interests
    user_interests = get_user_interests_list(user, min_score=1.0)
    logger.info(f"User {user.id} interests: {user_interests}")

    if not user_interests:
        logger.info("No user interests found, returning all posts")
        return base_posts

    # Get targeted posts (posts matching user interests)
    targeted_posts = get_posts_matching_interests(user_interests)
    targeted_count = targeted_posts.count()
    logger.info(f"Found {targeted_count} posts matching user interests")

    # If we have enough targeted posts, return them with some fallback posts
    if targeted_count > 0:
        # Calculate fallback posts to include
        fallback_count = max(1, int(targeted_count * fallback_limit))

        # Get random non-targeted posts as fallback
        excluded_ids = list(targeted_posts.values_list('id', flat=True))
        fallback_posts = base_posts.exclude(id__in=excluded_ids)[
            :fallback_count * 3]  # Get more to randomize

        if fallback_posts.exists():
            # Randomly select fallback posts
            fallback_list = list(fallback_posts)
            random.shuffle(fallback_list)
            fallback_selected = fallback_list[:fallback_count]
            fallback_ids = [post.id for post in fallback_selected]

            # Combine targeted and fallback posts
            combined_ids = list(targeted_posts.values_list(
                'id', flat=True)) + fallback_ids

            # Return combined queryset with randomized order within relevance groups
            return base_posts.filter(id__in=combined_ids).annotate(
                relevance_score=Case(
                    *[When(id__in=targeted_posts.values_list('id',
                           flat=True), then=Value(1.0))],
                    default=Value(0.5),
                    output_field=FloatField()
                )
                # Random order within each relevance group
            ).order_by('-relevance_score', '?')

        return targeted_posts

    # Fallback: return all posts if no matches found
    logger.info("No targeted posts found, returning all posts as fallback")
    return base_posts


def get_posts_matching_interests(interests_list):
    """
    Get posts that match any of the provided interests

    Args:
        interests_list: List of interest strings

    Returns:
        QuerySet of matching Post objects with relevance scoring
    """
    if not interests_list:
        return Post.objects.none()

    # Build Q objects for each interest
    q_objects = Q()
    interest_cases = []

    for i, interest in enumerate(interests_list):
        # Match posts where tags contain this interest
        q_objects |= Q(tags__icontains=interest)

        # Create case for relevance scoring (higher score for earlier interests)
        interest_cases.append(
            When(tags__icontains=interest, then=Value(len(interests_list) - i))
        )

    # Get matching posts with relevance scoring and randomization
    matching_posts = Post.objects.select_related('author').filter(q_objects).annotate(
        interest_score=Case(
            *interest_cases,
            default=Value(0),
            output_field=FloatField()
        )
        # Random order within each score group
    ).order_by('-interest_score', '?').distinct()

    return matching_posts


def get_user_interests_list(user, min_score=1.0, limit=10):
    """
    Get user's interests as a list of strings for post matching

    Args:
        user: User object
        min_score: Minimum interest score threshold
        limit: Maximum number of interests to return

    Returns:
        List of interest strings ordered by score
    """
    if not user:
        return []

    interests = UserInterest.objects.filter(
        user=user,
        score__gte=min_score
    ).order_by('-score').values_list('interest', flat=True)[:limit]

    return list(interests)


def mix_smart_posts_with_ads(posts_queryset, user=None, posts_per_page=10, ads_frequency=10):
    """
    Mix smart posts with advertisements maintaining the intelligent filtering

    Args:
        posts_queryset: Pre-filtered QuerySet of posts
        user: User object for ad targeting
        posts_per_page: Number of posts per page
        ads_frequency: Insert ad every N items

    Returns:
        List of mixed posts and ads
    """
    from feed.utils_ads import get_targeted_ad, get_user_interests, track_ad_impression

    mixed_items = []
    posts_list = list(posts_queryset[:posts_per_page])

    logger.info(f"=== MIX_SMART_POSTS_WITH_ADS DEBUG ===")
    logger.info(
        f"Input: {len(posts_list)} smart posts, ads_frequency: {ads_frequency}")
    logger.info(f"User: {user}")

    # Get user interests for ad targeting
    user_interests = get_user_interests(user, min_score=1.0, limit=10)
    logger.info(f"Found {len(user_interests)} user interests for ads")

    ads_inserted = 0
    for i, post in enumerate(posts_list):
        # Add the post
        mixed_items.append(post)
        logger.info(f"Added smart post {i+1}: {post.title}")

        # Check if we should add an ad
        should_add_ad = (i + 1) % ads_frequency == 0
        logger.info(f"Position {i+1}: should_add_ad = {should_add_ad}")

        if should_add_ad:
            logger.info(
                f"Attempting to get ad for position {len(mixed_items)}")
            ad = get_targeted_ad(user, user_interests)
            if ad:
                # Mark as advertisement for template rendering
                ad.type = 'advertisement'
                mixed_items.append(ad)
                ads_inserted += 1
                logger.info(
                    f"✓ Inserted ad {ad.id} at position {len(mixed_items)}")

                # Track impression
                # Triggers: When an ad is added to the HTML during server-side rendering
                track_ad_impression(ad)
            else:
                logger.error(
                    "❌ Failed to get ad - get_targeted_ad returned None")

    logger.info(f"=== FINAL RESULT ===")
    logger.info(
        f"Total items: {len(mixed_items)}, Smart posts: {len(posts_list)}, Ads inserted: {ads_inserted}")

    return mixed_items


def get_post_targeting_stats(user):
    """
    Get statistics about post targeting for a user

    Args:
        user: User object

    Returns:
        Dict with targeting statistics
    """
    if not user:
        return {
            'user_interests_count': 0,
            'total_posts': Post.objects.count(),
            'targeted_posts': 0,
            'targeting_ratio': 0.0
        }

    user_interests = get_user_interests_list(user)
    total_posts = Post.objects.count()

    if user_interests:
        targeted_posts = get_posts_matching_interests(user_interests).count()
    else:
        targeted_posts = 0

    targeting_ratio = (targeted_posts / max(total_posts, 1)) * 100

    return {
        'user_interests_count': len(user_interests),
        'user_interests': user_interests,
        'total_posts': total_posts,
        'targeted_posts': targeted_posts,
        'targeting_ratio': round(targeting_ratio, 1),
        'fallback_posts': total_posts - targeted_posts
    }


def debug_user_post_matching(user, limit=5):
    """
    Debug function to see how posts match user interests

    Args:
        user: User object
        limit: Number of posts to analyze

    Returns:
        List of debug info for each post
    """
    if not user:
        return []

    user_interests = get_user_interests_list(user)
    posts = Post.objects.order_by('-created_at')[:limit]

    debug_info = []
    for post in posts:
        matches = []
        for interest in user_interests:
            if interest.lower() in [tag.lower() for tag in post.tags]:
                matches.append(interest)

        debug_info.append({
            'post_id': post.id,
            'post_title': post.title,
            'post_tags': post.tags,
            'user_interests': user_interests,
            'matches': matches,
            'is_targeted': len(matches) > 0
        })

    return debug_info
