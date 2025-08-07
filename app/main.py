from dotenv import load_dotenv
from fastapi import FastAPI
import time
from fastapi.responses import JSONResponse
from fastapi import Request
from app.logger import setup_logger
from app.jobs.news import NewsAggregator
from app.jobs.ukraine import UkraineSummary
import asyncio

load_dotenv()
logger = setup_logger(__name__)

start_time = time.time()

app = FastAPI()

def format_uptime(seconds: float) -> str:
    if seconds < 5:
        return "just now"
    elif seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds // 60)} minutes"
    else:
        return f"{int(seconds // 3600)} hours"


@app.get("/health")
async def health_check(request: Request):
    uptime_seconds = time.time() - start_time
    formatted_uptime = format_uptime(uptime_seconds)

    health_data = {
        "status": 200,
        "uptime": formatted_uptime,
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": "🟢 NewsFeed Bot is running.",
    }

    return JSONResponse(status_code=200, content=health_data)


@app.on_event("startup")
async def start_scheduler():
    general_news_job = NewsAggregator(
        "0 */2 * * *",
        "General News Aggregator",
        topic="general",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=3,
    )  # every second hour UTC

    sport_news_job = NewsAggregator(
        "0 2 * * *",
        "🏈 Sport News Aggregator",
        topic="sports",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=24,
    )  # every day

    defense_news_job = NewsAggregator(
        "0 3 * * *",
        "🛡️ Defense News Aggregator",
        topic="defense",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=24,
    )  # every day

    environment_news_job = NewsAggregator(
        "0 4 * * *",
        "🌱 Environment News Aggregator",
        topic="environment",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=24,
    )  # every day

    tech_news_job = NewsAggregator(
        "0 5 * * *",
        "💻 Tech News Aggregator",
        topic="tech",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=24,
    )  # every day

    programming_news_job = NewsAggregator(
        "0 6 * * *",
        "👨‍💻 Programming News Aggregator",
        topic="programming",
        max_per_source=4,
        max_weighted_selection=10,
        max_articles=5,
        max_age_hours=24,
    )  # every day

    ukraine_summary_job = UkraineSummary("* 7 * * *", "Ukraine War Tracker")

    asyncio.create_task(general_news_job.start())
    asyncio.create_task(sport_news_job.start())
    asyncio.create_task(defense_news_job.start())
    asyncio.create_task(environment_news_job.start())
    asyncio.create_task(tech_news_job.start())
    asyncio.create_task(programming_news_job.start())
    asyncio.create_task(ukraine_summary_job.start())

    logger.info("✅ All jobs scheduled with staggered times.")
