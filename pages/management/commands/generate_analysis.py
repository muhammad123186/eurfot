from django.core.management.base import BaseCommand
from pages.analysis import run_all


class Command(BaseCommand):
    help = "Generate data-driven analysis articles"

    def handle(self, *args, **options):
        created = run_all()
        if not created:
            self.stdout.write("no new articles")
        for art in created:
            self.stdout.write(f"created: {art.title}")