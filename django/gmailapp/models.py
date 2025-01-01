from django.db import models
from django.contrib.auth.models import User
print('models file initiated')
class Gmail(models.Model):
    print('gmail models loaded')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_id = models.CharField(max_length=1000, default="123")
    thread_id = models.CharField(max_length=1000, default="123")

    def __str__(self):
        return self.message_id

