from django.urls import path

from .views import PostSearchView, UserSearchView

urlpatterns = [
    path("search/users/", UserSearchView.as_view(), name="search-users"),
    path("search/posts/", PostSearchView.as_view(), name="search-posts"),
]
