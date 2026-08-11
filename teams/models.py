from django.db import models
from datetime import datetime
x = [
   ("Premier League", "Premier League"),
    ("La Liga teams", "La Liga teams"),


]




class Team(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField(null=True, blank=True)   
    logo = models.ImageField(upload_to ='teams/%y/%m/%d/')
    founded = models.IntegerField()
    category = models.CharField(max_length=50, null=True, blank=True, choices=x)

    def __str__(self):
        return self.name

    




