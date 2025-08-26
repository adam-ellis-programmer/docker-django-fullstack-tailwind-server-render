# management/commands/seed_advertisements.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from feed.models import Advertisement
from decimal import Decimal
import sys

# ------- run command ---------
# docker-compose exec web python manage.py seed_advertisements
# ------- run command ---------


class Command(BaseCommand):
    help = 'Seed the database with sample advertisements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing advertisements before seeding',
        )

    def handle(self, *args, **options):
        """Main command handler"""

        # Clear existing ads if requested
        if options['clear']:
            self.stdout.write('🗑️  Clearing existing advertisements...')
            deleted_count = Advertisement.objects.all().delete()[0]
            print('delete info' )
            print(Advertisement.objects.all().delete())
            self.stdout.write(
                self.style.WARNING(
                    f'Deleted {deleted_count} existing advertisements')
            )

        # Import sample data from your data_ads.py file
        try:
            from feed.data_ads import sample_adverts
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    'Could not import sample_adverts from feed.data_ads\n'
                    'Make sure data_ads.py exists and contains sample_adverts array'
                )
            )
            sys.exit(1)

        self.stdout.write(f'🚀 Starting advertisement seeding...')
        self.stdout.write(
            f'📊 Found {len(sample_adverts)} advertisements to create')

        created_count = 0
        updated_count = 0
        error_count = 0

        for ad_data in sample_adverts:
            try:
                # Convert datetime to timezone-aware if needed
                created_at = ad_data.get('created_at')
                if created_at and timezone.is_naive(created_at):
                    created_at = timezone.make_aware(created_at)

                # Prepare the advertisement data
                ad_fields = {
                    'type': ad_data.get('type', 'advertisement'),
                    'brand': ad_data['brand'],
                    'title': ad_data['title'],
                    'text': ad_data['text'],
                    'image': ad_data['image'],
                    'cta_text': ad_data['cta_text'],
                    'cta_link': ad_data['cta_link'],
                    'category': ad_data['category'],
                    'promoted': ad_data.get('promoted', True),
                    'target_audience': ad_data.get('target_audience', []),
                    'budget_spent': Decimal(str(ad_data.get('budget_spent', 0.00))),
                    'impressions': ad_data.get('impressions', 0),
                    'clicks': ad_data.get('clicks', 0),
                    'is_active': ad_data.get('is_active', True),
                    'start_date': ad_data.get('start_date'),
                    'end_date': ad_data.get('end_date'),
                }

                # Add created_at if provided
                if created_at:
                    ad_fields['created_at'] = created_at

                # Use get_or_create to avoid duplicates
                ad, created = Advertisement.objects.get_or_create(
                    id=ad_data['id'],    # ← This is the LOOKUP key
                    defaults=ad_fields   # ← Only used if record doesn't exist
                )

                if created:
                    created_count += 1
                    self.stdout.write(f'  ✅ Created: {ad.brand} - {ad.title}')
                else:
                    # Update existing ad
                    for field, value in ad_fields.items():
                        setattr(ad, field, value)
                    ad.save()
                    updated_count += 1
                    self.stdout.write(f'  🔄 Updated: {ad.brand} - {ad.title}')

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ Error creating ad {ad_data.get("id", "unknown")}: {str(e)}'
                    )
                )

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Advertisement seeding completed!\n'
                f'   📈 Created: {created_count} new advertisements\n'
                f'   🔄 Updated: {updated_count} existing advertisements\n'
                f'   ❌ Errors: {error_count} failed attempts\n'
                f'   📊 Total processed: {len(sample_adverts)} advertisements'
            )
        )

        # Show some sample ads
        if created_count > 0 or updated_count > 0:
            self.stdout.write(f'\n🎯 Sample created advertisements:')
            sample_ads = Advertisement.objects.all()[:3]
            for ad in sample_ads:
                self.stdout.write(f'   • {ad.brand}: "{ad.title}"')
                self.stdout.write(f'     Targets: {ad.target_audience}')
                self.stdout.write(
                    f'     Budget: ${ad.budget_spent} | CTR: {ad.click_through_rate}%')

        # Database stats
        total_ads = Advertisement.objects.count()
        active_ads = Advertisement.objects.filter(is_active=True).count()

        self.stdout.write(f'\n📈 Database Statistics:')
        self.stdout.write(f'   Total advertisements: {total_ads}')
        self.stdout.write(f'   Active advertisements: {active_ads}')
        self.stdout.write(
            f'   Inactive advertisements: {total_ads - active_ads}')

        # Show targeting stats
        self.show_targeting_stats()

    def show_targeting_stats(self):
        """Display targeting statistics"""
        self.stdout.write(f'\n🎯 Targeting Analysis:')

        # Get all target audiences
        all_targets = []
        for ad in Advertisement.objects.all():
            all_targets.extend(ad.target_audience)

        # Count interest frequencies
        from collections import Counter
        interest_counts = Counter(all_targets)

        # Show top 10 targeted interests
        self.stdout.write(f'   Top targeted interests:')
        for interest, count in interest_counts.most_common(10):
            self.stdout.write(f'     • {interest}: {count} ads')
