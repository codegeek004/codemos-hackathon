from django.urls import path
from photos import views, auth

urlpatterns = [
    path('', views.home, name='photos_index'), 
    path('migrate/', views.migrate_photos, name='migrate_photos'), 
    path('auth/source/', auth.authenticate_source, name='authenticate_source'),
    path('auth/destination/', auth.authenticate_destination, name='authenticate_destination'),
    path('logout/', auth.logout_view, name='logout_source_and_destination'),
]