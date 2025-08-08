from datetime import datetime
import time
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, Info


class CronJobMetrics:
    """
    Handles all Prometheus metrics for cron jobs.
    """

    def __init__(self):
        # Prometheus metrics
        self.job_executions_total = Counter(
            "cron_job_executions_total",
            "Total number of cron job executions",
            ["job_name", "status"],  # status: success, error
        )

        self.job_duration_seconds = Histogram(
            "cron_job_duration_seconds",
            "Time spent executing cron jobs",
            ["job_name"],
            buckets=(
                0.1,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
                30.0,
                60.0,
                120.0,
                300.0,
                float("inf"),
            ),
        )

        self.job_last_success_timestamp = Gauge(
            "cron_job_last_success_timestamp",
            "Timestamp of the last successful job execution",
            ["job_name"],
        )

        self.job_last_execution_timestamp = Gauge(
            "cron_job_last_execution_timestamp",
            "Timestamp of the last job execution (success or failure)",
            ["job_name"],
        )

        self.job_next_execution_timestamp = Gauge(
            "cron_job_next_execution_timestamp",
            "Timestamp of the next scheduled job execution",
            ["job_name"],
        )

        self.job_info = Info(
            "cron_job_info", "Information about cron jobs", ["job_name"]
        )

        self.active_jobs = Gauge(
            "cron_jobs_active", "Number of currently active cron jobs"
        )

        self._active_jobs_count = 0

    def register_job(self, job_name: str, cron_expression: str, class_name: str):
        """Register a new cron job and set its info."""
        self.job_info.labels(job_name=job_name).info(
            {"cron_expression": cron_expression, "class_name": class_name}
        )

    def job_started(self, job_name: str):
        """Called when a cron job starts its loop."""
        self._active_jobs_count += 1
        self.active_jobs.set(self._active_jobs_count)

    def job_stopped(self, job_name: str):
        """Called when a cron job stops its loop."""
        self._active_jobs_count -= 1
        self.active_jobs.set(self._active_jobs_count)

    def execution_started(self, job_name: str) -> float:
        """Called when job execution starts. Returns start timestamp."""
        timestamp = time.time()
        self.job_last_execution_timestamp.labels(job_name=job_name).set(timestamp)
        return timestamp

    def execution_succeeded(self, job_name: str, start_time: float):
        """Called when job execution succeeds."""
        duration = time.time() - start_time
        self.job_executions_total.labels(job_name=job_name, status="success").inc()
        self.job_duration_seconds.labels(job_name=job_name).observe(duration)
        self.job_last_success_timestamp.labels(job_name=job_name).set(time.time())

    def execution_failed(self, job_name: str, start_time: float):
        """Called when job execution fails."""
        duration = time.time() - start_time
        self.job_executions_total.labels(job_name=job_name, status="error").inc()
        self.job_duration_seconds.labels(job_name=job_name).observe(duration)

    def next_execution_scheduled(self, job_name: str, next_run: datetime):
        """Called when next execution is scheduled."""
        self.job_next_execution_timestamp.labels(job_name=job_name).set(
            next_run.timestamp()
        )

    def get_active_jobs_count(self) -> int:
        """Returns the current count of active jobs."""
        return self._active_jobs_count


# Global metrics instance - singleton pattern
_metrics_instance: Optional[CronJobMetrics] = None


def get_metrics() -> CronJobMetrics:
    """Get the global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = CronJobMetrics()
    return _metrics_instance
