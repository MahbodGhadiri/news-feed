from abc import ABC, abstractmethod
from croniter import croniter
from datetime import datetime, timezone
import asyncio
from app.utils.logger import setup_logger
from app.metrics.cronjob import get_metrics


class AbstractCronJob(ABC):
    def __init__(
        self, cron_expression: str, job_name: str, enable_metrics: bool = True
    ):
        self.cron_expression = cron_expression
        self.job_name = job_name
        self.logger = setup_logger(self.__class__.__name__)
        self.enable_metrics = enable_metrics

        # Register with metrics if enabled
        if self.enable_metrics:
            self.metrics = get_metrics()
            self.metrics.register_job(
                self.job_name, self.cron_expression, self.__class__.__name__
            )

    @abstractmethod
    async def run(self):
        """
        This method should be implemented in subclasses to define the job's main logic.
        """
        pass

    async def _execute(self):
        """
        Wraps the run() method in try/except and handles logging.
        """
        start_time = None
        if self.enable_metrics:
            start_time = self.metrics.execution_started(self.job_name)

        try:
            self.logger.info(f"[{self.job_name}] ⏳ Starting scheduled job...")
            await self.run()
            self.logger.info(f"[{self.job_name}] ✅ Job completed successfully.")

            if self.enable_metrics and start_time is not None:
                self.metrics.execution_succeeded(self.job_name, start_time)

        except Exception as e:
            if self.enable_metrics and start_time is not None:
                self.metrics.execution_failed(self.job_name, start_time)

            self.logger.error(
                f"[{self.job_name}] ❌ Error in scheduled job: {e}", exc_info=True
            )

    async def start(self):
        """
        Starts the cron loop based on the cron expression.
        """
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
                    f"[{self.job_name}] 🕒 Next run at {next_run.isoformat()} "
                    f"(in {wait_seconds:.2f} seconds)"
                )

                await asyncio.sleep(wait_seconds)
                await self._execute()

        finally:
            if self.enable_metrics:
                self.metrics.job_stopped(self.job_name)
