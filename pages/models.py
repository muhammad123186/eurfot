from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User





class team(models.Model):
    team = models.CharField(max_length=100,null=True)
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)

    def __str__(self):
        return self.team


    
class stadium(models.Model):
    stadium = models.CharField(max_length=100,null=True)
    teams = models.OneToOneField(team, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.stadium    


class teams(models.Model):
     teams = models.CharField(max_length=100,)

     def __str__(self):
         return self.teams





class match(models.Model):

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('finished', 'Finished'),
    ]

    home_team = models.ForeignKey(team, on_delete=models.CASCADE, related_name='home_team')
    away_team = models.ForeignKey(team, on_delete=models.CASCADE, related_name='away_team')
    date = models.DateTimeField(null=True, blank=True)
    stadium = models.ForeignKey(stadium, on_delete=models.CASCADE, null=True)
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming'
    )
    
    
    def __str__(self):
        if self.date:
            return f"{self.home_team} vs {self.away_team} at {self.stadium} on {self.date.strftime('%Y-%m-%d %H:%M')} {self.home_score}:{self.away_score}"
        return f"{self.home_team} vs {self.away_team} {self.home_score}:{self.away_score}"


class Standing(models.Model):

    team = models.ForeignKey(team, on_delete=models.CASCADE)



    played = models.IntegerField(default=0)
    won = models.IntegerField(default=0)
    drawn = models.IntegerField(default=0)
    lost = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.team} - {self.points}"



class Prediction(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="predictions"
    )

    # معرف المباراة كما يرجعه المصدر الخارجي (fixture id)
    match_id = models.IntegerField()

    predicted_home_score = models.IntegerField(
    validators=[MinValueValidator(0)]
    )

    predicted_away_score = models.IntegerField(
    validators=[MinValueValidator(0)]
    )

    # النقاط المحسوبة بعد انتهاء المباراة (تبدأ فارغة، تُحسب لاحقاً)
    points_earned = models.IntegerField(
    null=True,
    blank=True,
    validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        # كل مستخدم يقدر يتوقع نتيجة مباراة معينة مرة وحدة بس
        unique_together = ("user", "match_id")

    def __str__(self):
        return f"{self.user.username} - match {self.match_id} - {self.predicted_home_score}:{self.predicted_away_score}"





class NewsArticle(models.Model):

    title = models.CharField(
        max_length=200
    )

    league_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="مثلاً PL, PD, SA... اتركه فاضي لو الخبر عام"
    )

    image = models.ImageField(
        upload_to="news_images/",
        blank=True,
        null=True
    )

    content = models.TextField()

    published_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title






class FanTeamOfWeek(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="fan_teams"
    )

    league_code = models.CharField(max_length=10)

    matchday = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "league_code", "matchday")

    def __str__(self):
        return f"{self.user.username} - {self.league_code} - MD{self.matchday}"


class FanTeamPlayer(models.Model):

    fan_team = models.ForeignKey(
        FanTeamOfWeek,
        on_delete=models.CASCADE,
        related_name="players"
    )

    player_id = models.IntegerField()

    player_name = models.CharField(
        max_length=150
    )

    team_name = models.CharField(
        max_length=150
    )

    team_logo = models.URLField(
        blank=True,
        null=True
    )

    position_group = models.CharField(
        max_length=50
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fan_team", "player_id"],
                name="unique_player_per_fan_team"
            )
        ]

    def __str__(self):
        return self.player_name




class Player(models.Model):

    api_id = models.IntegerField(
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    photo = models.URLField(
        null=True,
        blank=True
    )

    nationality = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    age = models.IntegerField(
        null=True,
        blank=True
    )

    position = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )


    team_name = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )


    team_logo = models.URLField(
        null=True,
        blank=True
    )


    def __str__(self):

        return self.name








 


          

       


     
        


            
