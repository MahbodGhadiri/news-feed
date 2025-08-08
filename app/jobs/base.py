from abc import ABC, abstractmethod
from croniter import croniter
from datetime import datetime, timezone
import asyncio
from app.utils.logger import setup_logger


class AbstractCronJob(ABC):
    def __init__(self, cron_expression: str, job_name: str):
        self.cron_expression = cron_expression
        self.job_name = job_name
        self.logger = setup_logger(self.__class__.__name__)

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
        try:
            self.logger.info(f"[{self.job_name}] ⏳ Starting scheduled job...")
            await self.run()
            self.logger.info(f"[{self.job_name}] ✅ Job completed successfully.")
        except Exception as e:
            self.logger.error(
                f"[{self.job_name}] ❌ Error in scheduled job: {e}", exc_info=True
            )

    async def start(self):
        """
        Starts the cron loop based on the cron expression.
        """
        self.logger.info(
            f"[{self.job_name}] 🔁 Cron job scheduled: {self.cron_expression}"
        )
        base_time = datetime.now(timezone.utc)
        iter = croniter(self.cron_expression, base_time)

        while True:
            next_run = iter.get_next(datetime)
            now = datetime.now(timezone.utc)
            wait_seconds = (next_run - now).total_seconds()

            self.logger.info(
                f"[{self.job_name}] 🕒 Next run at {next_run.isoformat()} "
                f"(in {wait_seconds:.2f} seconds)"
            )

            await asyncio.sleep(wait_seconds)
            await self._execute()
