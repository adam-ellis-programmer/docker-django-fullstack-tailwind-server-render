from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Post(models.Model):
    # Author relationship
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    
    # Post content
    title = models.CharField(max_length=200)
    text = models.TextField()
    image = models.URLField(max_length=500, blank=True, null=True)  # Using URLs for now
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