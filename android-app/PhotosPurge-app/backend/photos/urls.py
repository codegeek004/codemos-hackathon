from django.urls import path
from .views import log_migration, get_migrations

urlpatterns = [
    path("log/", log_migration),
    path("migrations/", get_migrations),
]

