from celery import shared_task

@shared_task
def update_residency_tracker():
    print("Update Tracker")
