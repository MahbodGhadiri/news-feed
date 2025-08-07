from app.ai import generate
from app.telegram import send_to_telegram
import json
from app.news import NewsAggregator
from app.logger import setup_logger


async def news_pipeline(
    topic: str,
    max_per_source: int,
    max_weighted_selection: int,
    max_articles: int,
    max_age_hours: int,
):
    logger = setup_logger(__name__)

    try:
        logger.info(
            f"⏳ Task started - aggregate {topic} news - max_age: {max_age_hours} hours and max_articles: {max_articles}"
        )
        aggregator = NewsAggregator(f"app/rss-feed/{topic}.txt")
        aggregator.filter_recent(max_age_hours).filter_summary().filter_duplicates()
        aggregator.score_by_keywords().limit_per_source(max_per_source)
        if len(aggregator.entries) == 0:
            logger.info("✅ done - no news found")

            return

        aggregator.weighted_selection(
            max_weighted_selection
        ).filter_duplicates().shuffle_and_slice(max_articles)

        summary_input = aggregator.summarize_prep()

        summary_json = generate(summary_input)

        headlines = json.loads(summary_json)["articles"]

        for headline in headlines:
            try:
                logger.info(f"sending to telegram")
                res = send_to_telegram(headline, topic)
                logger.info(res)
            except Exception as e:
                logger.error("failed to send article")
                logger.error(e)

        logger.info(f"✅ Task Ended - aggregated {topic} news")
    except Exception as e:
        logger.error("News Pipeline failed")
        logger.error(e)
