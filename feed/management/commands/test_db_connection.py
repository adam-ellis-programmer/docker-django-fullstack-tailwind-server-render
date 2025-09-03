# Create this file: feed/management/commands/test_db_connection.py

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Test database connection'

    def handle(self, *args, **options):
        try:
            # Test basic connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            self.stdout.write(
                self.style.SUCCESS(f'✅ Database connection successful!')
            )

            # Show current database info
            db_config = settings.DATABASES['default']
            self.stdout.write(f"Database: {db_config['NAME']}")
            self.stdout.write(f"Host: {db_config['HOST']}")
            self.stdout.write(f"Port: {db_config['PORT']}")
            self.stdout.write(f"User: {db_config['USER']}")

            # Test some queries
            with connection.cursor() as cursor:
                # Check if your tables exist
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name LIKE '%post%' OR table_name LIKE '%user%'
                """)
                tables = cursor.fetchall()

                if tables:
                    self.stdout.write("\n📋 Found these relevant tables:")
                    for table in tables:
                        self.stdout.write(f"  - {table[0]}")
                else:
                    self.stdout.write(
                        "\n⚠️  No tables found - you may need to run migrations")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database connection failed: {str(e)}')
            )
