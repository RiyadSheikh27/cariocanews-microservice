from django.urls import path
from .views import (
    RecommendationView,
    ZoneDetailView,
)
 
urlpatterns = [
    path("recommendations/",   RecommendationView.as_view(),  name="zone-recommendations"),
    path("<int:pk>/",          ZoneDetailView.as_view(),       name="zone-detail"),
]
 