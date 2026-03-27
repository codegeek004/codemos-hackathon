from django.urls import path
from drive import views
urlpatterns = [
    path('migrate/', views.migrate_drive,
         name='migrate_drive'),
]
