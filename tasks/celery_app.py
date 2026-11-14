from celery import Celery, chain, group
import os
from dotenv import load_dotenv
import time
from celery.schedules import crontab, schedule
from datetime import timedelta

load_dotenv()

celery_app = Celery('tasks', broker='redis://localhost', backend=os.environ.get('MONGO_DB'))

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    result_persistent=True,  # Ensure results are stored persistently
    task_chord_propogates=True,
)


@celery_app.task
def initial_task():
    """
    Mimics an initial database call with a delay.
    """
    print("Initial DB operation starting.")
    time.sleep(5)  # Simulate DB delay
    print("Initial DB operation completed.")
    return "Initial done"

@celery_app.task
def parallel_task_1(*args, **kwargs):
    """
    First parallel task.
    """
    print("Running parallel task 1")
    time.sleep(2)  # Simulate some operation
    return "Result from task 1"

@celery_app.task
def parallel_task_2(*args, **kwargs):
    """
    Second parallel task.
    """
    print("Running parallel task 2")
    time.sleep(3)  # Simulate some operation
    return "Result from task 2"

@celery_app.task
def final_task(results):
    """
    Aggregates results and mimics another DB operation.
    """
    print("Aggregating results:", results)
    time.sleep(5)  # Simulate final DB delay
    return "Aggregated results: " + str(results)

workflow = chain(
    initial_task.s(),
    group(
        parallel_task_1.s(),
        parallel_task_2.s()
    ),
    final_task.s()
)


@celery_app.task(name='workflow.tasks')
def start_workflow():
    """
    Starts the defined workflow chain.
    """
    workflow.apply_async()


celery_app.conf.beat_schedule = {
    'run-workflow-every-2-minutes': {
        'task': 'workflow.tasks',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
        'options': {'expires': 300},       # Optional: Prevent overlapping tasks
        'args': (),                        # No arguments for now
    },
}
