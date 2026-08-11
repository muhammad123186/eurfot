from django.core.management.base import BaseCommand
from pages.models import Prediction
from pages.views import headers
import requests


class Command(BaseCommand):

    help = "حساب نقاط توقعات المستخدمين للمباريات المنتهية"

    FINISHED_STATUSES = {"FT", "AET", "PEN"}

    def handle(self, *args, **options):

        pending_predictions = Prediction.objects.filter(
            points_earned__isnull=True
        )

        match_ids = pending_predictions.values_list(
            "match_id", flat=True
        ).distinct()

        for match_id in match_ids:

            result = self.fetch_match_result(match_id)

            if result is None:
                self.stdout.write(f"مباراة {match_id}: لسا ما خلصت أو فشل الطلب")
                continue

            home_actual, away_actual = result

            predictions = pending_predictions.filter(match_id=match_id)

            for prediction in predictions:

                points = self.calculate_points(
                    prediction.predicted_home_score,
                    prediction.predicted_away_score,
                    home_actual,
                    away_actual,
                )

                prediction.points_earned = points
                prediction.save()

                self.stdout.write(
                    f"مباراة {match_id}: {prediction.user.username} توقع "
                    f"{prediction.predicted_home_score}-{prediction.predicted_away_score} "
                    f"| النتيجة الفعلية {home_actual}-{away_actual} "
                    f"| النقاط: {points}"
                )

    def fetch_match_result(self, match_id):

        try:
            response = requests.get(
                "https://v3.football.api-sports.io/fixtures",
                headers=headers,
                params={"id": match_id},
                timeout=15,
            )

            data = response.json()

        except requests.RequestException:
            return None

        fixtures = data.get("response", [])

        if not fixtures:
            return None

        fixture = fixtures[0]

        status = fixture["fixture"]["status"]["short"]

        if status not in self.FINISHED_STATUSES:
            return None

        home_actual = fixture["goals"]["home"]
        away_actual = fixture["goals"]["away"]

        if home_actual is None or away_actual is None:
            return None

        return home_actual, away_actual

    def calculate_points(self, pred_home, pred_away, actual_home, actual_away):

        if pred_home == actual_home and pred_away == actual_away:
            return 3

        pred_outcome = self.get_outcome(pred_home, pred_away)
        actual_outcome = self.get_outcome(actual_home, actual_away)

        if pred_outcome == actual_outcome:
            return 1

        return 0

    def get_outcome(self, home, away):

        if home > away:
            return "home"
        elif away > home:
            return "away"
        else:
            return "draw"

            