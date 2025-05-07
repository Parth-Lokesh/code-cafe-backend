# urls.py
from django.urls import path
from .views import GitHubAuthView

urlpatterns = [
    path("auth/github/callback/", GitHubAuthView),
]
