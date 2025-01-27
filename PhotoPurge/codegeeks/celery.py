from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codegeeks.settings')

app = Celery('codegeeks')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related config keys should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_url = 'redis://localhost:6379/0'  # Redis on localhost
app.conf.result_backend = 'redis://localhost:6379/0'

app.conf.update(result_expires=5400)

# Load task modules from all registered Django app configs.
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()
