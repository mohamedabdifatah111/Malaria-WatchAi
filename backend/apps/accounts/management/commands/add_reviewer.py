from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.permissions import REVIEWER_GROUP


class Command(BaseCommand):
    help = "Add an existing user to the reviewer group."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError("User not found.")
        group, _ = Group.objects.get_or_create(name=REVIEWER_GROUP)
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now a reviewer.")) 