from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now, localtime
from django.contrib.auth.models import User


class CustomUser(AbstractUser):
    last_active = models.DateTimeField(null=True, blank=True, default=now())

# It keeps track of deleted emails
class TaskStatus(models.Model):
    user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE) 
    task_id = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=40, default="PENDING")
    result = models.TextField(null=True, blank=True)
    deleted_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

# it keeps track of recovered emails
class RecoverStatus(models.Model):
    user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE)  
    task_id = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=40, default="PENDING")
    result = models.TextField(null=True, blank=True)
    recover_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
