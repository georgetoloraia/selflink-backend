from django.urls import path

from apps.astro import views

urlpatterns = [
    path("astro/natal/", views.NatalChartView.as_view(), name="astro-natal-create"),
    path("astro/natal/me/", views.MyNatalChartView.as_view(), name="astro-natal-me"),
]
