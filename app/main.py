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
@repeat_every(hour=6)
async def on_startup():
    print("test")
    # await news_pipeline()


async def news_pipeline():
    try:
        aggregator = NewsAggregator()

        aggregator.filter_recent(6).filter_summary().filter_duplicates()
        aggregator.score_by_keywords().limit_per_source()
        aggregator.weighted_selection().filter_duplicates().shuffle_and_slice()

        summary_input = aggregator.summarize_prep()

        summary_json = generate(summary_input)

        headlines = json.loads(summary_json)["articles"]

        for headline in headlines:
            send_to_telegram(headline)
    except Exception as e:
        print("News Pipeline failed")
        print(e)
    
    
