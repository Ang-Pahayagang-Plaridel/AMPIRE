from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AMPIRE.settings')

app = Celery('AMPIRE')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

CELERY_BEAT_SCHEDULE = {
    'edit-gsheet-every-hour': {
        'task': 'sirk.task.compute_sirk',
        'schedule': crontab(minute=0, hour='*'),  # Runs every hour at minute 0
        # 'schedule': crontab(minute=0),  # every hour
        # 'schedule': crontab(minute='*/5'),  # Runs every 10 minutes
    },
}