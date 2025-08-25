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
# ADVERTS MODEL
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
