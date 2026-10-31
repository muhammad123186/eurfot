from django.core.management.base import BaseCommand
from pages.analysis import run_all


class Command(BaseCommand):
    help = "Generate data-driven analysis articles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Rewrite existing articles in place with the latest content",
        )

    def handle(self, *args, **options):
        made = run_all(force=options["rebuild"])
        if not made:
            self.stdout.write("no new articles")
        for art in made:
            self.stdout.write(f"saved: {art.title}")