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

    async def run(self):
        return await self.news_pipeline()

    async def news_pipeline(self):

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
            return

        aggregator.weighted_selection(
            self.max_weighted_selection
        ).filter_duplicates().shuffle_and_slice(self.max_articles)

        summary_input = aggregator.summarize_prep()

        if not summary_input.strip():
            self.logger.info("✅ done - no news found")
            return

        llm_client = GeminiClient()

        headlines = llm_client.generate(summary_input)["articles"]

        for headline in headlines:
            try:
                self.article_service.create_article(
                    headline["title"],
                    headline["summary"],
                    headline["sources"][0],
                    sent_to_telegram=True,
                )
                send_to_telegram(headline, self.topic)
            except Exception as e:
                self.logger.error("failed to send article")
                self.logger.error(e)

        self.logger.info(f"✅ Task Ended - aggregated {self.topic} news")
        return True
