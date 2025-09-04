# Replace these functions in your feed/utils.py
from django.db import models  # For F() expressions
from feed.models import Advertisement, UserInterest
import random
import logging
import time

logger = logging.getLogger(__name__)

# Global cache variables (better than function attributes)
_ad_cache = None
_ad_cache_time = 0
CACHE_TIMEOUT = 300  # 5 minutes


def get_targeted_ad(user=None, user_interests=None):
    """
    OPTIMIZED: Get a targeted advertisement with aggressive caching
    """
    global _ad_cache, _ad_cache_time

    start_time = time.time()
    current_time = time.time()

    # Check if cache is valid (within 5 minutes)
    if _ad_cache is None or (current_time - _ad_cache_time) > CACHE_TIMEOUT:
        print("🔄 Refreshing ad cache (cache miss or expired)")
        cache_start = time.time()

        # Get ALL active ads in one query
        active_ads = list(Advertisement.objects.filter(is_active=True))

        # Filter for campaign-active ads (this might be the slow part)
        campaign_active_ads = []
        for ad in active_ads:
            # If is_campaign_active is a property that hits the database, this is your bottleneck
            if ad.is_campaign_active:
                campaign_active_ads.append(ad)

        cache_time = time.time() - cache_start
        print(
            f"📊 Ad cache refresh took: {cache_time:.3f}s for {len(campaign_active_ads)} ads")

        # Update global cache
        _ad_cache = campaign_active_ads
        _ad_cache_time = current_time
    else:
        print("✅ Using cached ads")

    campaign_active_ads = _ad_cache

    if not campaign_active_ads:
        print("❌ No campaign-active advertisements found")
        return None

    # Quick targeting logic (this part was already fast)
    if user_interests and hasattr(user_interests, 'exists') and user_interests.exists():
        interest_names = [interest.interest for interest in user_interests]

        targeted_ads = []
        for ad in campaign_active_ads:
            if hasattr(ad, 'target_audience') and ad.target_audience:
                matches = set(ad.target_audience) & set(interest_names)
                if matches:
                    targeted_ads.extend([ad] * len(matches))

        if targeted_ads:
            selected_ad = random.choice(targeted_ads)
            print(f"✅ Selected targeted ad: {selected_ad.id}")
            return selected_ad

    # Fallback: return random active ad
    selected_ad = random.choice(campaign_active_ads)
    total_time = time.time() - start_time
    print(f"✅ Selected random ad: {selected_ad.id} (took {total_time:.3f}s)")
    return selected_ad


def clear_ad_cache():
    """Call this when ads are updated"""
    global _ad_cache, _ad_cache_time
    _ad_cache = None
    _ad_cache_time = 0
    print("🗑️ Ad cache cleared")


def get_user_interests(user, min_score=1.0, limit=10):
    """
    OPTIMIZED: Get user interests with caching
    """
    if not user:
        return UserInterest.objects.none()

    # Simple in-memory cache for user interests
    cache_key = f"user_interests_{user.id}"
    cache_timeout = 600  # 10 minutes

    # Check if we have cached interests for this user
    if not hasattr(get_user_interests, '_cache'):
        get_user_interests._cache = {}

    cached_data = get_user_interests._cache.get(cache_key)
    current_time = time.time()

    if cached_data and (current_time - cached_data['time']) < cache_timeout:
        print(f"✅ Using cached interests for user {user.id}")
        return cached_data['interests']

    print(f"🔄 Loading interests for user {user.id}")
    interests = list(UserInterest.objects.filter(
        user=user,
        score__gte=min_score
    ).order_by('-score')[:limit])

    # Cache the results
    get_user_interests._cache[cache_key] = {
        'interests': interests,
        'time': current_time
    }

    return interests


def mix_posts_with_ads(posts, user=None, ads_frequency=10):
    """
    OPTIMIZED: Mix posts with advertisements
    """
    start_time = time.time()
    mixed_items = []
    post_list = list(posts)

    print(
        f"🔄 Mixing {len(post_list)} posts with ads (frequency: {ads_frequency})")

    # Get user interests ONCE at the start
    interests_start = time.time()
    user_interests = get_user_interests(user, min_score=1.0, limit=10)
    interests_time = time.time() - interests_start
    print(f"📊 User interests query took: {interests_time:.3f}s")

    ads_inserted = 0
    for i, post in enumerate(post_list):
        # Add the post
        mixed_items.append(post)

        # Check if we should add an ad
        should_add_ad = (i + 1) % ads_frequency == 0

        if should_add_ad:
            ad_start = time.time()
            ad = get_targeted_ad(user, user_interests)
            ad_time = time.time() - ad_start
            print(f"📊 Single ad selection took: {ad_time:.3f}s")

            if ad:
                # Mark as advertisement for template rendering
                ad.type = 'advertisement'
                mixed_items.append(ad)
                ads_inserted += 1
                print(f"✅ Inserted ad {ad.id}")

                # Track impression (this might also be slow)
                track_start = time.time()
                track_ad_impression(ad)
                track_time = time.time() - track_start
                print(f"📊 Ad impression tracking took: {track_time:.3f}s")

    total_time = time.time() - start_time
    print(
        f"📊 Total mix_posts_with_ads time: {total_time:.3f}s ({ads_inserted} ads)")

    return mixed_items


def track_ad_impression(ad):
    """
    OPTIMIZED: Track ad impression (avoid individual saves)
    """
    try:
        # Use update() instead of save() for better performance
        Advertisement.objects.filter(id=ad.id).update(
            impressions=models.F('impressions') + 1
        )
        print(f"✅ Tracked impression for ad {ad.id}")
    except Exception as e:
        print(f"❌ Failed to track impression for ad {ad.id}: {e}")


# Keep your other functions the same...
def track_ad_click(ad_id):
    """Track ad click for analytics"""
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
