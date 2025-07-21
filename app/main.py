from dotenv import load_dotenv
from app.ai import generate
from app.telegram import send_to_telegram
import json
from app.news import NewsAggregator
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every

load_dotenv()

app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=1*60*60)
async def aggregate_general_news():
    await news_pipeline("general", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=3)

# @app.on_event("startup")
# @repeat_every(seconds=24*60*60)
# async def aggregate_sport_news():
#     await news_pipeline("sports", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=24)

# @app.on_event("startup")
# @repeat_every(seconds=24*60*60)
# async def aggregate_defense_news():
#     await news_pipeline("defense", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=24)

# @app.on_event("startup")
# @repeat_every(seconds=24*60*60)
# async def aggregate_environment_news():
#     await news_pipeline("environment", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=24)

# @app.on_event("startup")
# @repeat_every(seconds=24*60*60)
# async def aggregate_tech_news():
#     await news_pipeline("tech", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=24)

# @app.on_event("startup")
# @repeat_every(seconds=72*60*60)
# async def aggregate_programming_news():
#     await news_pipeline("programming", max_per_source= 4, max_weighted_selection= 10, max_articles= 5, max_age_hours=72)




async def news_pipeline(topic: str, max_per_source: int, max_weighted_selection: int, max_articles: int, max_age_hours: int):
    try:
        print(f"⏳ Task started - aggregate {topic} news - max_age: {max_age_hours} hours and max_articles: {max_articles}")
        aggregator = NewsAggregator(f"app/rss-feed/{topic}.txt")
        aggregator.filter_recent(max_age_hours).filter_summary().filter_duplicates()
        aggregator.score_by_keywords().limit_per_source(max_per_source)
        if(len(aggregator.entries) == 0):
            print("no news found")
            print("✅ done")
            return

        aggregator.weighted_selection(max_weighted_selection).filter_duplicates().shuffle_and_slice(max_articles)

        summary_input = aggregator.summarize_prep()

        summary_json = generate(summary_input)

        headlines = json.loads(summary_json)["articles"]

        for headline in headlines:
            print(f"sending to telegram")
            res = send_to_telegram(headline, topic)
            print(res)
        print(f"✅ Task Ended - aggregated {topic} news")
    except Exception as e:
        print("News Pipeline failed")
        print(e)
    
    
