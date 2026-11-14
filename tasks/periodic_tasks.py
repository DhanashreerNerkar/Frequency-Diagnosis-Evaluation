from .celery_app import celery_app
import time

@celery_app.task(bind=True, name='periodic_tasks.my_periodic_task')
def my_periodic_task(self):
    """
    A simple periodic task that logs a message.
    """
    print("Periodic task is running!")
    time.sleep(5)
    return "Task completed"
