from app.jobs.base import AbstractCronJob
from app.db.article_service import ArticleService
from app.utils.ai import GeminiClient
from app.utils.telegram import send_to_telegram
from app.utils.news import NewsAggregatorTool


class NewsAggregator(AbstractCronJob):
    def __init__(
        self,
        article_service: ArticleService,
        cron_expression: str,
        job_name: str,
        topic: str,
        max_per_source: int,
        max_weighted_selection: int,
        max_articles: int,
        max_age_hours: int,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = topic
        self.article_service = article_service
        self.max_per_source = max_per_source
        self.max_weighted_selection = max_weighted_selection
        self.max_articles = max_articles
        self.max_age_hours = max_age_hours

    def run(self):  # Changed from async to sync
        """
        Main job execution method - now synchronous to run in thread pool
        """
        return self.news_pipeline()

    def news_pipeline(self):  # Changed from async to sync
        """
        Synchronous news aggregation pipeline
        """
        self.logger.info(
            f"⏳ Task started - aggregate {self.topic} news - max_age: {self.max_age_hours} hours and max_articles: {self.max_articles}"
        )

        aggregator = NewsAggregatorTool(f"app/rss-feed/{self.topic}.txt")
        aggregator.filter_recent(
            self.max_age_hours
        ).filter_summary().filter_duplicates()
        aggregator.score_by_keywords().limit_per_source(self.max_per_source)

        if len(aggregator.entries) == 0:
            self.logger.info("✅ done - no news found")
            return True

        aggregator.weighted_selection(
            self.max_weighted_selection
        ).filter_duplicates().shuffle_and_slice(self.max_articles)

        summary_input = aggregator.summarize_prep()

        if not summary_input.strip():
            self.logger.info("✅ done - no news found")
            return True

        llm_client = GeminiClient()
        headlines = llm_client.generate(summary_input)["articles"]

        for headline in headlines:
            try:
                self.article_service.create_article(
                    headline["title"],
                    headline["summary"],
                    headline["sources"][0],
                    farsi_title=headline["farsi_title"],
                    farsi_summary=headline["farsi_summary"],
                    sent_to_telegram=True,
                )

                send_to_telegram(headline, self.topic, locale="english")
                send_to_telegram(headline, self.topic, locale="farsi")

            except Exception as e:
                self.logger.error(f"Failed to send article: {e}")

        self.logger.info(f"✅ Task Ended - aggregated {self.topic} news")
        return True
