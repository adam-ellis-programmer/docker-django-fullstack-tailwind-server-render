from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class AppUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    """
    # Additional fields beyond the default User model
    email = models.EmailField(
        unique=True, help_text='Required. Enter a valid email address.')
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True,
                           help_text='Tell us about yourself')
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)

    # Profile settings
    is_email_verified = models.BooleanField(default=False)
    newsletter_subscription = models.BooleanField(default=True)
    privacy_settings = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # Make email the primary identifier instead of username
    # -- tells Django what field to use for authentication/login.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Required for createsuperuser

    class Meta:
        db_table = 'app_users'
        verbose_name = 'App User'
        verbose_name_plural = 'App Users'
    # Defines how your model instance appears as a string
    # Django admin interface (in dropdowns, lists)
    # Python shell when you print a user object
    # Anywhere Python needs to convert your object to a string
    def __str__(self):
        return f"{self.email} ({self.username})"

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.username

    # NO parentheses! needed to be called 
    @property
    def age(self):
        """Calculate user's age from birth_date"""
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
