from django.db import models

# Create your models here.
class AuthenticationToken(models.Model):
	source_token = models.CharField(max_length=100)
	dest_token = models.CharField(max_length=100)
	