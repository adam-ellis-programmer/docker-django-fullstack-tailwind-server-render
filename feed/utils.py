# feed/utils.py

from feed.models import Advertisement, UserInterest
import random
import logging

logger = logging.getLogger(__name__)


def get_targeted_ad(user=None, user_interests=None):
    """
    Get a targeted advertisement based on user interests

    Args:
        user: User object (optional)
        user_interests: QuerySet of UserInterest objects (optional)

    Returns:
        Advertisement object or None
    """
    # Get active advertisements
    active_ads = Advertisement.objects.filter(is_active=True)
    logger.info(f"Found {active_ads.count()} ads with is_active=True")

    # Check campaign active status for each ad (can't filter on properties)
    campaign_active_ads = []
    for ad in active_ads:
        is_campaign_active = ad.is_campaign_active
        logger.info(f"Ad {ad.id}: is_campaign_active = {is_campaign_active}")
        if is_campaign_active:
            campaign_active_ads.append(ad)

    logger.info(f"Found {len(campaign_active_ads)} campaign-active ads")

    if not campaign_active_ads:
        logger.warning("No campaign-active advertisements found")
        # FALLBACK: Just use is_active ads if campaign check fails
        if active_ads.exists():
            logger.info("Using fallback: returning random is_active ad")
            selected_ad = random.choice(active_ads)
            logger.info(f"Selected fallback ad: {selected_ad.id}")
            return selected_ad
        return None

    # If user has interests, try to find matching ads
    if user_interests and user_interests.exists():
        interest_names = [interest.interest for interest in user_interests]
        logger.info(f"User interests: {interest_names}")

        # Find ads that target user's interests
        targeted_ads = []
        for ad in campaign_active_ads:
            if ad.target_audience:
                # Check if any ad target matches user interests
                matches = set(ad.target_audience) & set(interest_names)
                if matches:
                    logger.info(f"Ad {ad.id} matches interests: {matches}")
                    # Weight ad by number of matching interests
                    targeted_ads.extend([ad] * len(matches))

        if targeted_ads:
            selected_ad = random.choice(targeted_ads)
            logger.info(f"Selected targeted ad: {selected_ad.id}")
            return selected_ad

    # Fallback: return random active ad
    selected_ad = random.choice(campaign_active_ads)
    logger.info(f"Selected random campaign-active ad: {selected_ad.id}")
    return selected_ad


def get_user_interests(user, min_score=1.0, limit=10):
    """
    Get user's top interests for ad targeting

    Args:
        user: User object
        min_score: Minimum interest score threshold
        limit: Maximum number of interests to return

    Returns:
        QuerySet of UserInterest objects ordered by score
    """
    if not user:
        return UserInterest.objects.none()

    return UserInterest.objects.filter(
        user=user,
        score__gte=min_score
    ).order_by('-score')[:limit]


def mix_posts_with_ads(posts, user=None, ads_frequency=10):
    """
    Mix posts with advertisements at specified frequency

    Args:
        posts: QuerySet or list of Post objects
        user: User object for ad targeting
        ads_frequency: Insert ad every N posts

    Returns:
        List of mixed posts and ads
    """
    mixed_items = []
    post_list = list(posts)

    logger.info(f"=== MIX_POSTS_WITH_ADS DEBUG ===")
    logger.info(
        f"Input: {len(post_list)} posts, ads_frequency: {ads_frequency}")
    logger.info(f"User: {user}")

    # Get user interests for ad targeting
    user_interests = get_user_interests(user, min_score=1.0, limit=10)
    logger.info(f"Found {user_interests.count()} user interests")

    ads_inserted = 0
    for i, post in enumerate(post_list):
        # Add the post
        mixed_items.append(post)
        logger.info(f"Added post {i+1}: {post.title}")

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
                track_ad_impression(ad)
            else:
                logger.error(
                    "❌ Failed to get ad - get_targeted_ad returned None")

    logger.info(f"=== FINAL RESULT ===")
    logger.info(
        f"Total items: {len(mixed_items)}, Ads inserted: {ads_inserted}")

    return mixed_items


def track_ad_impression(ad):
    """
    Track ad impression for analytics

    Args:
        ad: Advertisement object
    """
    try:
        ad.impressions += 1
        ad.save(update_fields=['impressions'])
        logger.info(f"Tracked impression for ad {ad.id}: {ad.impressions}")
    except Exception as e:
        logger.error(f"Failed to track impression for ad {ad.id}: {e}")


def track_ad_click(ad_id):
    """
    Track ad click for analytics

    Args:
        ad_id: Advertisement ID string

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ad = Advertisement.objects.get(id=ad_id)
        ad.clicks += 1
        ad.save(update_fields=['clicks'])
        logger.info(f"Tracked click for ad {ad_id}: {ad.clicks}")
        return True
    except Advertisement.DoesNotExist:
        logger.error(f"Ad {ad_id} not found for click tracking")
        return False
    except Exception as e:
        logger.error(f"Failed to track click for ad {ad_id}: {e}")
        return False


def get_ad_performance_stats(ad_id=None):
    """
    Get advertisement performance statistics

    Args:
        ad_id: Optional specific ad ID, otherwise returns all ads

    Returns:
        QuerySet or dict with performance metrics
    """
    if ad_id:
        try:
            ad = Advertisement.objects.get(id=ad_id)
            return {
                'id': ad.id,
                'brand': ad.brand,
                'impressions': ad.impressions,
                'clicks': ad.clicks,
                'ctr': ad.click_through_rate,
                'cpc': ad.cost_per_click
            }
        except Advertisement.DoesNotExist:
            return None

    # Return all active ads with performance data
    return Advertisement.objects.filter(is_active=True).values(
        'id', 'brand', 'impressions', 'clicks', 'budget_spent'
    )
