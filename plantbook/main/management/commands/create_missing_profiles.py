from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Profile
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates profiles for users who do not have one'

    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0

        for user in users:
            try:
                user.profile
            except Profile.DoesNotExist:
                Profile.objects.create(
                    user=user,
                    joined_date=timezone.now()
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created profile for user {user.email}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} profiles')
        ) 