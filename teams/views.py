from django.shortcuts import render
from .models import Team


def team(request, id):
    team = Team.objects.get(id=id)
    return render(request, 'teams/team.html', {'team': team})

def teams(request):
    teams = Team.objects.all()
    return render(request, 'teams/teams.html' , {'teams': teams})

def matches(request):
    matchs = match.objects.all()
    return render(request, 'teams/matches.html' , {'matc': matchs})
    