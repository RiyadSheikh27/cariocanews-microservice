from django.urls import path
from .views import (
    RecommendationView,
    ZoneDetailView,
    BookmarkListView,
    BookmarkDetailView,
    ZoneCompareView,
)
 
urlpatterns = [
    path("recommendations/",   RecommendationView.as_view(),  name="zone-recommendations"),
    path("<int:pk>/",          ZoneDetailView.as_view(),       name="zone-detail"),
    path("bookmarks/",         BookmarkListView.as_view(),     name="bookmark-list"),
    path("bookmarks/<int:pk>/", BookmarkDetailView.as_view(),  name="bookmark-detail"),
    path("compare/",            ZoneCompareView.as_view(),      name="zone-compare"),
]
 