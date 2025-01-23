from photos import views, auth
from django.urls import include, path
from photos import views

urlpatterns = [
    path('migrate/', views.migrate_photos, name='migrate_photos'),  # Migrate photos
    path('destination/auth/', auth.destination_google_auth, name='destination_google_auth'),  # Destination auth
    path('destination/auth/callback/', auth.destination_google_auth_callback, name='destination_google_auth_callback'),  # Destination callback
]
