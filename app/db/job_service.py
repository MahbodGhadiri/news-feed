from datetime import datetime
from app.db.base_service import BaseDatabaseService


class CronJobDBService(BaseDatabaseService):
    def __init__(self, db_url: str = None):
        super().__init__(db_url)
        self._schema()

    def _schema(self):
        """Ensure cron_job_runs table exists."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_job_runs (
                id SERIAL PRIMARY KEY,
                job_name TEXT NOT NULL,
                scheduled_time TIMESTAMPTZ NOT NULL,
                retry_count INT DEFAULT 0,
                status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed')) DEFAULT 'pending',
                last_error TEXT,
                duration_seconds NUMERIC,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """
        )
        conn.commit()
        cur.close()
        conn.close()

    def create_job_run(self, job_name: str, scheduled_time: datetime):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cron_job_runs (job_name, scheduled_time)
            VALUES (%s, %s)
            RETURNING id;
        """,
            (job_name, scheduled_time),
        )
        job_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return job_id

    def get_hanging_jobs(self, job_name: str) -> list:
        """Jobs stuck in 'running' state after crash."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, scheduled_time, retry_count
            FROM cron_job_runs
            WHERE job_name = %s
              AND status != 'completed'
              AND retry_count < 3
            ORDER BY scheduled_time ASC;
        """,
            (job_name,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "scheduled_time": r[1], "retry_count": r[2]} for r in rows]

    def mark_job_running(self, job_id: int):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE cron_job_runs
            SET status = 'running', updated_at = NOW()
            WHERE id = %s;
        """,
            (job_id,),
        )
        conn.commit()
        cur.close()
        conn.close()

    def mark_job_completed(self, job_id: int, duration: float):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE cron_job_runs
            SET status = 'completed', duration_seconds = %s, updated_at = NOW()
            WHERE id = %s;
        """,
            (duration, job_id),
        )
        conn.commit()
        cur.close()
        conn.close()

    def mark_job_failed(self, job_id: int, error_message: str, duration: float):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE cron_job_runs
            SET status = 'failed',
                retry_count = retry_count + 1,
                last_error = %s,
                duration_seconds = %s,
                updated_at = NOW()
            WHERE id = %s;
        """,
            (error_message, duration, job_id),
        )
        conn.commit()
        cur.close()
        conn.close()
