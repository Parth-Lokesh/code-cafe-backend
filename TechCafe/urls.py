# urls.py
from django.urls import path
from .views import GitHubAuthView,join_queue_view,queue_status_view,simulate_room_view

urlpatterns = [
    path("auth/github/callback/", GitHubAuthView),
    path("queue/join/", join_queue_view, name="join-queue"),
    path("queue/status/", queue_status_view, name="queue-status"),
    path("queue/simulate/", simulate_room_view, name="simulate-room"),
]
