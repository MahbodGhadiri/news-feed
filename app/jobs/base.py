from abc import ABC, abstractmethod
from croniter import croniter
from datetime import datetime, timezone
import asyncio
import time
from app.utils.logger import setup_logger
from app.metrics.cronjob import get_metrics
from app.db.job_service import CronJobDBService


class AbstractCronJob(ABC):
    def __init__(
        self,
        cron_expression: str,
        job_name: str,
        enable_metrics: bool = True,
        max_retries: int = 3,
    ):
        self.cron_expression = cron_expression
        self.job_name = job_name
        self.logger = setup_logger(self.__class__.__name__)
        self.enable_metrics = enable_metrics
        self.max_retries = max_retries
        self.db_service = CronJobDBService()

        if self.enable_metrics:
            self.metrics = get_metrics()
            self.metrics.register_job(
                self.job_name, self.cron_expression, self.__class__.__name__
            )

        self._retry_hanging_jobs()

    def _retry_hanging_jobs(self):
        hanging_jobs = self.db_service.get_hanging_jobs(self.job_name)
        if hanging_jobs:
            self.logger.info(
                f"[{self.job_name}] 🔄 Found {len(hanging_jobs)} hanging jobs from crash. Retrying..."
            )
            for job in hanging_jobs:
                asyncio.create_task(
                    self._execute(
                        job_id=job["id"],
                        scheduled_time=job["scheduled_time"],
                        attempt=job["retry_count"],
                    )
                )

    @abstractmethod
    def run(self) -> bool:
        """
        Implement in subclasses - synchronous method.
        Must return True if succeeded, False if failed.
        """
        pass

    async def _execute(
        self, job_id: int = None, scheduled_time: datetime = None, attempt: int = 0
    ):
        if job_id is None:
            scheduled_time = datetime.now(timezone.utc)
            job_id = self.db_service.create_job_run(self.job_name, scheduled_time)

        while attempt <= self.max_retries:
            self.db_service.mark_job_running(job_id)
            start_time = time.monotonic()
            start_metric_time = None

            if self.enable_metrics:
                start_metric_time = self.metrics.execution_started(self.job_name)

            try:
                self.logger.info(
                    f"[{self.job_name}] Attempt {attempt+1} ⏳ Starting scheduled job..."
                )

                success = await asyncio.to_thread(self.run)

                duration = round(time.monotonic() - start_time, 2)

                if success:
                    self.logger.info(
                        f"[{self.job_name}] ✅ Job completed in {duration}s."
                    )
                    self.db_service.mark_job_completed(job_id, duration)
                    if self.enable_metrics and start_metric_time is not None:
                        self.metrics.execution_succeeded(
                            self.job_name, start_metric_time
                        )
                    return
                else:
                    raise Exception("Job returned failure flag.")

            except Exception as e:
                duration = round(time.monotonic() - start_time, 2)
                self.logger.error(
                    f"[{self.job_name}] ❌ Error in job: {e}", exc_info=True
                )
                self.db_service.mark_job_failed(job_id, str(e), duration)
                if self.enable_metrics and start_metric_time is not None:
                    self.metrics.execution_failed(self.job_name, start_metric_time)

                attempt += 1
                if attempt > self.max_retries:
                    self.logger.error(
                        f"[{self.job_name}] 🚫 Max retries reached ({self.max_retries}). Giving up."
                    )
                    break

                self.logger.info(f"[{self.job_name}] 🔁 Retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def start(self):
        if self.enable_metrics:
            self.metrics.job_started(self.job_name)

        try:
            self.logger.info(
                f"[{self.job_name}] 🔁 Cron job scheduled: {self.cron_expression}"
            )
            base_time = datetime.now(timezone.utc)
            iter = croniter(self.cron_expression, base_time)

            while True:
                next_run = iter.get_next(datetime)
                now = datetime.now(timezone.utc)
                wait_seconds = (next_run - now).total_seconds()

                if self.enable_metrics:
                    self.metrics.next_execution_scheduled(self.job_name, next_run)

                self.logger.info(
                    f"[{self.job_name}] 🕒 Next run at {next_run.isoformat()} (in {wait_seconds:.2f} seconds)"
                )

                await asyncio.sleep(wait_seconds)
                # Fire and forget
                asyncio.create_task(self._execute())

        finally:
            if self.enable_metrics:
                self.metrics.job_stopped(self.job_name)
