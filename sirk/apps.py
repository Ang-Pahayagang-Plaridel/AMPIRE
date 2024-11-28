from django.apps import AppConfig
from django.db.models.signals import post_migrate


class SirkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sirk'

    def ready(self):

        from .models import OnlinePoints

        def create_initial_online_sirk_pts(sender, **kwargs):
            if not OnlinePoints.objects.exists():
                OnlinePoints.objects.create(
                    rule='Personal Screenshot',
                    value=1,
                )
                OnlinePoints.objects.create(
                    rule='IG Story',
                    value=1,
                )
                OnlinePoints.objects.create(
                    rule='FB-TWT Share',
                    value=5,
                )
                OnlinePoints.objects.create(
                    rule='Interactive Isyu',
                    value=3,
                )
                OnlinePoints.objects.create(
                    rule='Reply-React',
                    value=2,
                )
                OnlinePoints.objects.create(
                    rule='Professors',
                    value=5,
                )
                OnlinePoints.objects.create(
                    rule='APP FB Page Like',
                    value=10,
                )
                OnlinePoints.objects.create(
                    rule='APP TWT-IG Follow',
                    value=10,
                )
                OnlinePoints.objects.create(
                    rule='Telegram',
                    value=5,
                )
        post_migrate.connect(create_initial_online_sirk_pts)

        from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

        def create_periodic_tasks(sender, **kwargs):
            # Define the schedule (e.g., every hour)
            # schedule, created = IntervalSchedule.objects.get_or_create(
            #     every=30,
            #     period=IntervalSchedule.MINUTES,
            # )
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute='0,30',  # Run at minute 0 and 30 of each hour
                hour='*',       # Every hour
            )

            # Define the periodic task
            task, created = PeriodicTask.objects.get_or_create(
                interval=schedule,
                name='Compute Sirk',
                task='sirk.task.compute_sirk',
            )
        post_migrate.connect(create_periodic_tasks, sender=self)