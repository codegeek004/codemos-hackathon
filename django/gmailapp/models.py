from django.db import models
from django.contrib.auth.models import User

class TaskStatus(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	task_id = models.CharField(max_length=200, unique=True)
	status = models.CharField(max_length=40, default="PENDING")
	result = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	
