import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse
from app.utils.logger import setup_logger


class BaseDatabaseService:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise RuntimeError("DATABASE_URL environment variable is not set.")

        self.logger = setup_logger(self.__class__.__name__)
        self.parsed_url = urlparse(self.db_url)

        self.dbname = self.parsed_url.path.lstrip("/")
        self.user = self.parsed_url.username
        self.password = self.parsed_url.password
        self.host = self.parsed_url.hostname
        self.port = self.parsed_url.port or 5432

        self._ensure_database_exists()

    def _ensure_database_exists(self):
        conn = psycopg2.connect(
            dbname="postgres",
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (self.dbname,))
        exists = cur.fetchone()

        if not exists:
            self.logger.info(f"Database '{self.dbname}' not found. Creating...")
            cur.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.dbname))
            )

        else:
            self.logger.info(f"Database '{self.dbname}' already exists.")

        cur.close()
        conn.close()

    def get_connection(self):
        connection = psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        self.logger.debug("Connected to database.")
        return connection
