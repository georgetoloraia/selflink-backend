from django.urls import path

from .views import MatrixProfileView, MatrixSyncView

urlpatterns = [
    path("matrix/profile/", MatrixProfileView.as_view(), name="matrix-profile"),
    path("matrix/sync/", MatrixSyncView.as_view(), name="matrix-sync"),
]
