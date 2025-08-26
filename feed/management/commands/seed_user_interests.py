# feed/management/commands/seed_user_interests.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from feed.models import UserInterest, Post
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed user interests based on existing post interactions'

    def handle(self, *args, **options):
        self.stdout.write('Starting to seed user interests...')

        # Get all users and posts
        users = User.objects.all()
        posts = Post.objects.all()

        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found. Please create users first.'))
            return

        if not posts.exists():
            self.stdout.write(self.style.ERROR('No posts found. Please create posts first.'))
            return

        created_interests = 0

        # For each user, simulate interests based on post tags
        for user in users:
            # Get a sample of posts (simulate user viewing habits)
            viewed_posts = random.sample(list(posts), min(len(posts), random.randint(5, 15)))
            
            user_interest_scores = {}
            
            for post in viewed_posts:
                # Simulate different interaction types with random weights
                interaction_types = ['view_30s', 'like', 'comment', 'share', 'save']
                weights = [0.8, 0.3, 0.1, 0.05, 0.15]  # Probabilities for each interaction
                
                for tag in post.tags:
                    if tag not in user_interest_scores:
                        user_interest_scores[tag] = 0
                    
                    # Simulate user interactions
                    for interaction, prob in zip(interaction_types, weights):
                        if random.random() < prob:
                            # Add weight based on interaction type
                            interaction_weights = {
                                'view_30s': 1.0,
                                'like': 1.0,
                                'comment': 2.0,
                                'share': 3.0,
                                'save': 2.0,
                            }
                            user_interest_scores[tag] += interaction_weights[interaction]
            
            # Create UserInterest objects
            for interest, score in user_interest_scores.items():
                if score > 0:  # Only create if there's some interest
                    # Cap the score at 10.0
                    final_score = min(10.0, score)
                    
                    user_interest, created = UserInterest.objects.get_or_create(
                        user=user,
                        interest=interest,
                        defaults={'score': final_score}
                    )
                    
                    if created:
                        created_interests += 1
                        self.stdout.write(f'Created interest: {user.username} -> {interest} (score: {final_score:.1f})')
                    else:
                        # Update existing score
                        user_interest.score = final_score
                        user_interest.save()
                        self.stdout.write(f'Updated interest: {user.username} -> {interest} (score: {final_score:.1f})')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created/updated {created_interests} user interests for {users.count()} users'
            )
        )

        # Show some statistics
        self.stdout.write('\nUser Interest Statistics:')
        for user in users[:5]:  # Show first 5 users
            user_interests = UserInterest.objects.filter(user=user).order_by('-score')[:5]
            if user_interests:
                self.stdout.write(f'\n{user.username} top interests:')
                for interest in user_interests:
                    self.stdout.write(f'  - {interest.interest}: {interest.score:.1f}')