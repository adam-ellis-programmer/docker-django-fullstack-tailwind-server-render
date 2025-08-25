from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
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
