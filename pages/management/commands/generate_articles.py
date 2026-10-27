from django.core.management.base import BaseCommand
from pages.analysis import run_all
from pages.team_analysis import run_team_articles


class Command(BaseCommand):
    help = "Generate data-driven analysis articles"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=1, help="عدد الأيام (1 = اليوم فقط)")
        parser.add_argument("--force", action="store_true", help="إعادة بناء المعاينات الموجودة")
        parser.add_argument("--only-previews", action="store_true", help="تخطّي run_all القديم")

    def handle(self, *args, **options):
        created = []
        if not options["only_previews"]:
            created += list(run_all() or [])
        created += run_team_articles(days=options["days"], force=options["force"])

        if not created:
            self.stdout.write("no new articles")
        for art in created:
            self.stdout.write(f"created: {art.title}")