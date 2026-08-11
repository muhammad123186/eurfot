from django.urls import path
from . import views


urlpatterns = [   
    path('team/', views.team, name='team'),
    path('teams/', views.teams, name='teams'),
    path('team/<int:id>/', views.team, name='team'),
    
]


