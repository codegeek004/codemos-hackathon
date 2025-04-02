from django.db import models
from django.contrib.auth.models import User

class MigrationRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    google_email = models.EmailField()
    total_photos = models.IntegerField()
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("completed", "Completed")])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.google_email} - {self.status}"

