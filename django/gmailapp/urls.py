from django.urls import path
from . import views

urlpatterns = [
    path('', views.show, name='shows'),
    path('delete/', views.delete_emails_view, name='delete_emails'),
    path('fetch-token/', views.fetch_google_token, name='fetch_google_token'),

]
