from django.urls import path

from apps.matching import views

urlpatterns = [
    path("soulmatch/with/<int:user_id>/", views.SoulmatchWithView.as_view(), name="soulmatch-with"),
    path("soulmatch/recommendations/", views.SoulmatchRecommendationsView.as_view(), name="soulmatch-recommendations"),
]
