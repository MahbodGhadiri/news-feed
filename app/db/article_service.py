import uuid
from app.db.base_service import BaseDatabaseService


class ArticleService:
    def __init__(self, db_service: BaseDatabaseService):
        self.db_service = db_service
        self.logger = db_service.logger
        self._init_schema()

    def _init_schema(self):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title TEXT NOT NULL UNIQUE,
                summary TEXT,
                source TEXT NOT NULL,
                sent_to_telegram BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            );
        """
        )

        cur.execute(
            """
            DO $$
            BEGIN
                -- Add farsi_title column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'articles' AND column_name = 'farsi_title'
                ) THEN
                    ALTER TABLE articles ADD COLUMN farsi_title TEXT NULL;
                END IF;
                
                -- Add farsi_summary column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'articles' AND column_name = 'farsi_summary'
                ) THEN
                    ALTER TABLE articles ADD COLUMN farsi_summary TEXT NULL;
                END IF;
            END
            $$;
        """
        )

        cur.execute(
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """
        )

        cur.execute(
            """
            DROP TRIGGER IF EXISTS set_updated_at ON articles;
            CREATE TRIGGER set_updated_at
            BEFORE UPDATE ON articles
            FOR EACH ROW
            EXECUTE PROCEDURE update_updated_at_column();
        """
        )

        conn.commit()
        cur.close()
        conn.close()
        self.logger.info("Article schema and triggers initialized with auto-migration.")

    def create_article(
        self,
        title: str,
        summary: str,
        source: str,
        sent_to_telegram=False,
        farsi_title: str = None,
        farsi_summary: str = None,
    ):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO articles (title, summary, source, sent_to_telegram, farsi_title, farsi_summary)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (title) DO NOTHING
            RETURNING id;
        """,
            (title, summary, source, sent_to_telegram, farsi_title, farsi_summary),
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if row:
            article_id = row[0]
            self.logger.info(f"Created article {article_id}")
            return str(article_id)
        else:
            self.logger.info(
                f"Skipped insert: article with title '{title}' already exists."
            )
            return None

    def get_article(self, article_id):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, title, summary, source, sent_to_telegram, created_at, updated_at, farsi_title, farsi_summary
            FROM articles
            WHERE id = %s;
        """,
            (uuid.UUID(article_id),),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "id": str(row[0]),
                "title": row[1],
                "summary": row[2],
                "source": row[3],
                "sent_to_telegram": row[4],
                "created_at": row[5].isoformat(),
                "updated_at": row[6].isoformat(),
                "farsi_title": row[7],
                "farsi_summary": row[8],
            }
        return None

    def update_article(
        self,
        article_id,
        title=None,
        summary=None,
        source=None,
        sent_to_telegram=None,
        farsi_title=None,
        farsi_summary=None,
    ):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        fields = []
        values = []

        if title is not None:
            fields.append("title = %s")
            values.append(title)
        if summary is not None:
            fields.append("summary = %s")
            values.append(summary)
        if source is not None:
            fields.append("source = %s")
            values.append(source)
        if sent_to_telegram is not None:
            fields.append("sent_to_telegram = %s")
            values.append(sent_to_telegram)
        if farsi_title is not None:
            fields.append("farsi_title = %s")
            values.append(farsi_title)
        if farsi_summary is not None:
            fields.append("farsi_summary = %s")
            values.append(farsi_summary)

        if not fields:
            return False

        values.append(uuid.UUID(article_id))

        query = f"UPDATE articles SET {', '.join(fields)} WHERE id = %s;"
        cur.execute(query, tuple(values))

        conn.commit()
        cur.close()
        conn.close()

        self.logger.info(f"Updated article {article_id}")
        return True

    def delete_article(self, article_id):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM articles WHERE id = %s;", (uuid.UUID(article_id),))
        deleted = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        self.logger.info(
            f"Deleted article {article_id}"
            if deleted
            else f"No article found for {article_id}"
        )
        return deleted > 0

    def list_articles_filtered(
        self, source=None, search=None, start_date=None, end_date=None, limit=20
    ):
        conn = self.db_service.get_connection()
        cur = conn.cursor()

        query = """
            SELECT id, title, summary, source, sent_to_telegram, created_at, farsi_title, farsi_summary
            FROM articles
            WHERE 1=1
        """
        params = []

        if source:
            query += " AND source = %s"
            params.append(source)

        if search:
            query += " AND (title ILIKE %s OR summary ILIKE %s OR farsi_title ILIKE %s OR farsi_summary ILIKE %s)"
            like_term = f"%{search}%"
            params.extend([like_term, like_term, like_term, like_term])

        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)

        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "summary": row[2],
                "source": row[3],
                "sent_to_telegram": row[4],
                "created_at": row[5],
                "farsi_title": row[6],
                "farsi_summary": row[7],
            }
            for row in rows
        ]
