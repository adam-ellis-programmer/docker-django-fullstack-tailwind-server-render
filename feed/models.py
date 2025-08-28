import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


logger = logging.getLogger(__name__)


# docker-compose exec web python manage.py makemigrations feed
# docker-compose exec web python manage.py migrate


# ========================================================================
# POST MODEL
# ========================================================================


class Post(models.Model):
    # Author relationship
    # Django's Automatic Field Naming: author_id
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='posts')

    # Post content
    title = models.CharField(max_length=200)
    text = models.TextField()
    image = models.URLField(max_length=500, blank=True,
                            null=True)  # Using URLs for now
    location = models.CharField(max_length=200, blank=True, null=True)

    # Engagement metrics
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)

    # Tags (using JSONField for simplicity)
    tags = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feed_posts'
        ordering = ['-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    @property
    def engagement_rate(self):
        """Calculate basic engagement rate"""
        total_engagement = self.likes + self.comments + self.shares
        return total_engagement


# ========================================================================
# ADVERTS MODEL -- Smart Ad Targeting
# ========================================================================


class Advertisement(models.Model):
    """Model for storing advertisement data"""

    # Basic ad information
    # 'ad_001', 'ad_002', etc.
    id = models.CharField(max_length=50, primary_key=True)
    type = models.CharField(max_length=50, default='advertisement')
    brand = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    text = models.TextField()
    image = models.URLField(max_length=500)

    # Call-to-action
    cta_text = models.CharField(
        max_length=100, help_text='Button text like "Shop Now"')
    cta_link = models.URLField(
        max_length=500, help_text='Link when CTA button is clicked')

    # Categorization
    category = models.CharField(
        max_length=100, help_text='e.g., Outdoor Gear, Health & Wellness')
    promoted = models.BooleanField(default=True)

    # Targeting (using JSONField like your Post tags)
    target_audience = models.JSONField(
        default=list, blank=True, help_text='List of interests to target')

    # Analytics & Budget
    budget_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    impressions = models.PositiveIntegerField(
        default=0, help_text='Number of times ad was shown')
    clicks = models.PositiveIntegerField(
        default=0, help_text='Number of times ad was clicked')

    # Status fields
    is_active = models.BooleanField(
        default=True, help_text='Whether ad is currently active')
    start_date = models.DateTimeField(
        null=True, blank=True, help_text='When ad campaign starts')
    end_date = models.DateTimeField(
        null=True, blank=True, help_text='When ad campaign ends')

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feed_advertisements'
        ordering = ['-created_at']
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'

    def __str__(self):
        return f"{self.brand} - {self.title}"

    @property
    def click_through_rate(self):
        """Calculate CTR percentage"""
        if self.impressions > 0:
            return round((self.clicks / self.impressions) * 100, 2)
        return 0.0

    @property
    def cost_per_click(self):
        """Calculate CPC"""
        if self.clicks > 0:
            return round(float(self.budget_spent) / self.clicks, 2)
        return 0.0

    @property
    def is_campaign_active(self):
        """Check if ad campaign is currently active"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


# ========================================================================
# User Interest MODEL -- Smart Ad Targeting
# ========================================================================


class UserInterest(models.Model):
    """Track user interests based on their interactions"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='interests')
    interest = models.CharField(
        max_length=100, help_text='Interest name from post tags')
    score = models.FloatField(default=1.0, help_text='Interest strength score')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_interests'
        unique_together = ['user', 'interest']  # One row per user per interest
        ordering = ['-score', 'interest']
        verbose_name = 'User Interest'
        verbose_name_plural = 'User Interests'

    def __str__(self):
        return f"{self.user.username} - {self.interest}: {self.score}"


# Interest weight configuration
INTEREST_WEIGHTS = {
    'view_30s': 1.0,      # Views for 30+ seconds
    'like': 1.0,          # Likes post
    'comment': 2.0,       # Comments on post
    'share': 3.0,         # Shares post
    'save': 2.0,          # Saves post
    'view_10s': 0.5,      # Brief view
    'click_profile': 1.5,  # Clicks on author profile
}


def update_user_interest(user, interest, action_type):
    """
    Update user interest score based on action

    Args:
        user: User object
        interest: Interest string (from post tags)
        action_type: Type of action ('like', 'comment', 'share', etc.)
    """
    weight = INTEREST_WEIGHTS.get(action_type, 1.0)

    # Get or create interest record
    interest_obj, created = UserInterest.objects.get_or_create(
        user=user,
        interest=interest,
        defaults={'score': weight}
    )

    if not created:
        # Add to existing score with diminishing returns
        current_score = interest_obj.score

        # Apply diminishing returns to prevent score explosion
        if current_score < 3.0:
            actual_weight = weight  # Full weight
        elif current_score < 6.0:
            actual_weight = weight * 0.7  # Reduced weight
        elif current_score < 9.0:
            actual_weight = weight * 0.4  # Much reduced
        else:
            actual_weight = weight * 0.1  # Minimal weight

        # Cap at 10.0 maximum
        interest_obj.score = min(10.0, current_score + actual_weight)
        interest_obj.save()

    return interest_obj


def process_user_interaction(user, post, action_type):
    """
    Process user interaction with a post and update interests

    Args:
        user: User who performed action
        post: Post object
        action_type: Type of interaction
    """
    # Update interest for each tag in the post
    for tag in post.tags:
        update_user_interest(user, tag, action_type)


def get_user_interests(user, min_score=1.0, limit=10):
    """
    Get user's top interests above minimum score

    Returns: QuerySet of UserInterest objects
    """
    return UserInterest.objects.filter(
        user=user,
        score__gte=min_score
    ).order_by('-score')[:limit]


def get_user_interest_dict(user, min_score=1.0):
    """
    Get user interests as dictionary for ad matching

    Returns: Dict like {'hiking': 5.2, 'photography': 3.1}
    """
    interests = UserInterest.objects.filter(
        user=user,
        score__gte=min_score
    ).values_list('interest', 'score')

    return dict(interests)

# ========================================================================
# Post Impression MODEL -- Smart Ad Targeting
# ========================================================================
# The on_delete=models.CASCADE means that if a User or Post is deleted,
# their related PostImpression records will also be deleted automatically.


class PostImpression(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    impression_time = models.DateTimeField(auto_now_add=True)
    view_duration = models.FloatField(
        default=0.0, help_text='Duration in seconds')
    scroll_depth = models.FloatField(
        default=0.0, help_text='Percentage of post visible (0.0-1.0)')
    interaction_type = models.CharField(
        max_length=50, default='view', help_text='view, click, like, etc.')

    class Meta:
        db_table = 'post_impressions'
        unique_together = ['user', 'post']  # Prevent duplicate impressions
        ordering = ['-impression_time']
        verbose_name = 'Post Impression'
        verbose_name_plural = 'Post Impressions'

    def __str__(self):
        return f"{self.user.username} viewed {self.post.title} for {self.view_duration}s"

# ========================================================================
# POST LIKE MODEL -- Track User-Post Like Relationships
# ========================================================================


# post_like.user - gives you the full User object
# post_like.user_id - gives you just the integer ID
# post_like.user.username - access user attributes through the relationship
# The related_name='post_likes' allows reverse lookups:
    # user.post_likes.all() - get all PostLike objects for this user
    # user.post_likes.count() - count how many posts this user has liked
class PostLike(models.Model):
    """Track which users have liked which posts"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='post_likes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='user_likes'
    )

    # Timestamp for analytics
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_likes'
        unique_together = ['user', 'post']  # Prevent duplicate likes
        ordering = ['-created_at']
        verbose_name = 'Post Like'
        verbose_name_plural = 'Post Likes'
        indexes = [
            models.Index(fields=['user']),  # Fast lookup of user's likes
            models.Index(fields=['post']),  # Fast lookup of post's likes
            models.Index(fields=['created_at']),  # Analytics queries
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"


# ========================================================================
# ADVERT TRACKIGN -- Track User-Post Like Relationships
# ========================================================================

# Add this to your feed/models.py file after the existing models

class AdImpression(models.Model):
    """Track ad impressions for analytics"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ad_impressions',
        null=True,
        blank=True  # Allow anonymous users
    )
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='impressions_tracked'
    )

    # Viewing metrics
    view_duration = models.FloatField(
        default=0.0,
        help_text='How long user viewed ad in seconds'
    )
    viewport_percentage = models.FloatField(
        default=0.0,
        help_text='Percentage of ad visible (0.0-1.0)'
    )

    # Session and device info
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text='Session key for anonymous users'
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text='User agent string'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='User IP address'
    )

    # Timing
    impression_start = models.DateTimeField(auto_now_add=True)
    impression_end = models.DateTimeField(null=True, blank=True)

    # Flags
    is_valid_impression = models.BooleanField(
        default=True,
        help_text='Whether this counts as a valid impression (>= 1 second view)'
    )
    counted_in_analytics = models.BooleanField(
        default=False,
        help_text='Whether this impression has been counted in ad analytics'
    )

    class Meta:
        db_table = 'ad_impressions'
        ordering = ['-impression_start']
        verbose_name = 'Ad Impression'
        verbose_name_plural = 'Ad Impressions'
        indexes = [
            models.Index(fields=['user', 'advertisement']),
            models.Index(fields=['session_key', 'advertisement']),
            models.Index(fields=['impression_start']),
            models.Index(fields=['is_valid_impression']),
        ]
        # Prevent duplicate impressions within short timeframe
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['user', 'advertisement', 'impression_start'],
        #         name='unique_user_ad_impression_per_minute',
        #         condition=models.Q(impression_start__isnull=False)
        #     )
        # ]

    def __str__(self):
        user_identifier = self.user.username if self.user else f"Session: {self.session_key}"
        return f"{user_identifier} viewed {self.advertisement.id} for {self.view_duration}s"

    @property
    def total_view_time(self):
        """Calculate total view time"""
        if self.impression_end:
            return (self.impression_end - self.impression_start).total_seconds()
        return self.view_duration

    def mark_as_ended(self, duration_seconds=None):
        """Mark impression as ended"""
        self.impression_end = timezone.now()
        if duration_seconds is not None:
            self.view_duration = duration_seconds

        # Determine if this is a valid impression (>= 1 second)
        self.is_valid_impression = self.view_duration >= 1.0
        self.save()


# Utility functions for ad impression tracking

def create_ad_impression(advertisement, user=None, request=None):
    """
    Create a new ad impression record
    """
    try:
        # Get session key and IP for anonymous users
        session_key = None
        ip_address = None
        user_agent = None

        if request:
            session_key = request.session.session_key or request.session.create()
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        # TEMPORARILY COMMENTED OUT FOR TESTING
        # # Check for recent duplicate impression (within last minute)
        # recent_cutoff = timezone.now() - timezone.timedelta(minutes=1)
        #
        # duplicate_check = AdImpression.objects.filter(
        #     advertisement=advertisement,
        #     impression_start__gte=recent_cutoff
        # )
        #
        # if user:
        #     duplicate_check = duplicate_check.filter(user=user)
        # elif session_key:
        #     duplicate_check = duplicate_check.filter(session_key=session_key)
        #
        # if duplicate_check.exists():
        #     logger.info(
        #         f"Duplicate ad impression prevented for ad {advertisement.id}")
        #     return None

        # Create new impression
        impression = AdImpression.objects.create(
            user=user,
            advertisement=advertisement,
            session_key=session_key,
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(
            f"Created ad impression {impression.id} for ad {advertisement.id}")
        return impression

    except Exception as e:
        logger.error(f"Error creating ad impression: {e}")
        return None


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def update_ad_impression_duration(impression_id, duration_seconds, viewport_percentage=None):
    """
    Update ad impression with viewing duration

    Args:
        impression_id: AdImpression ID
        duration_seconds: How long the ad was viewed
        viewport_percentage: Percentage of ad visible (optional)
    """
    try:
        impression = AdImpression.objects.get(id=impression_id)
        impression.view_duration = duration_seconds

        if viewport_percentage is not None:
            impression.viewport_percentage = viewport_percentage

        impression.is_valid_impression = duration_seconds >= 1.0
        impression.mark_as_ended(duration_seconds)

        logger.info(
            f"Updated ad impression {impression_id}: {duration_seconds}s view")
        return True

    except AdImpression.DoesNotExist:
        logger.error(f"Ad impression {impression_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error updating ad impression: {e}")
        return False
