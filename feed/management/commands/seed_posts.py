from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from feed.models import Post
from feed.data import temp_posts  # Import your existing data
from datetime import datetime, timedelta
import random
from pprint import pprint
User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with sample posts and users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--posts',
            type=int,
            default=100,
            help='Number of posts to create (default: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing posts before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing posts...')
            Post.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Posts cleared!'))

        # Create sample users if they don't exist
        self.create_sample_users()

        # Create posts
        num_posts = min(options['posts'], len(temp_posts))  # Use imported data
        self.create_posts(num_posts)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded {num_posts} posts!'
            )
        )

    '''
    The Key Difference
    LanguageSyntax Pattern Reading Order 

    Python value_if_true if condition else value_if_falseValue first, then condition 
    JavaScript condition ? value_if_true : value_if_falseCondition first, then values
    '''

    def create_sample_users(self):
        """Create sample users based on the posts data"""
        # Extract unique authors from temp_posts
        unique_authors = {}
        for post_data in temp_posts:
            author_key = post_data['username']
            if author_key not in unique_authors:
                unique_authors[author_key] = {
                    'username': post_data['username'].replace('@', ''),
                    'email': f"{post_data['username'].replace('@', '')}@example.com",
                    'first_name': post_data['author'].split()[0],
                    'last_name': ' '.join(post_data['author'].split()[1:]) if len(post_data['author'].split()) > 1 else '',
                    'bio': f"Adventure and fitness enthusiast from {post_data.get('location', 'Unknown')}"
                }
        pprint(unique_authors)
        # ============================
        pprint(unique_authors.values())
        # ============================
        # Create users
        for user_data in unique_authors.values():
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password('11111111')
                user.save()
                self.stdout.write(f'Created user: {user.email}')

    def create_posts(self, num_posts):
        """Create posts using the imported temp_posts data"""
        users = list(User.objects.all())

        # Create a mapping of usernames to User objects
        username_to_user = {}
        for user in users:
            username_to_user[user.username] = user

        for i in range(num_posts):
            post_data = temp_posts[i]

            # Find the user by username, or assign random user
            username = post_data['username'].replace('@', '')
            author = username_to_user.get(username, random.choice(users))

            post = Post.objects.create(
                author=author,
                title=post_data['title'],
                text=post_data['text'],
                image=post_data['image'],
                location=post_data.get('location', ''),
                likes=post_data['likes'],
                comments=post_data['comments'],
                shares=post_data['shares'],
                tags=post_data['tags'],
                created_at=post_data['timestamp']
            )

            if i % 10 == 0:  # Progress indicator
                self.stdout.write(f'Created {i+1} posts...')
