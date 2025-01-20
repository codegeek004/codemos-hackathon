from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now

class CustomUser(AbstractUser):
    last_active = models.DateTimeField(default=now)
    # Add related_name to avoid reverse accessor clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',  # Change the related name here
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',  # Change the related name here
        blank=True
    )

class TaskStatus(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE) 
    task_id = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=40, default="PENDING")
    result = models.TextField(null=True, blank=True)
    deleted_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class RecoverStatus(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  
    task_id = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=40, default="PENDING")
    result = models.TextField(null=True, blank=True)
    recover_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
