from celery import Celery
import redis
import time

# Redis DB 0 = broker (job queue), DB 1 = result backend (optional, separate to avoid clutter)
celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,  # auto-clean old results after 1 hour
)

# Separate raw redis client for progress writes (fine-grained %, not just start/done)
progress_store = redis.Redis(host="localhost", port=6379, db=2, decode_responses=True)


@celery.task(bind=True)
def process_file(self, job_id: str, path: str):
    progress_store.set(f"progress:{job_id}", 0)
    progress_store.set(f"status:{job_id}", "processing")

    try:
        total_steps = 10
        for i in range(total_steps):
            time.sleep(1)  # replace with real chunked processing of the file at `path`
            pct = int((i + 1) / total_steps * 100)
            progress_store.set(f"progress:{job_id}", pct)

        progress_store.set(f"status:{job_id}", "done")
    except Exception as e:
        progress_store.set(f"status:{job_id}", "failed")
        progress_store.set(f"error:{job_id}", str(e))
        raise