from fastapi import APIRouter, Response, Query
from app.db.base_service import BaseDatabaseService
from app.db.article_service import ArticleService
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
import os

router = APIRouter()

base_service = BaseDatabaseService()
article_service = ArticleService(base_service)


@router.get("/rss", response_class=Response)
def get_rss(
    source: Optional[str] = Query(None, description="Filter by source URL"),
    search: Optional[str] = Query(None, description="Search in title or summary"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Limit number of articles"),
):
    domain = os.environ.get("SERVER_URL")

    # Parse dates if provided
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # Fetch filtered articles
    articles = article_service.list_articles_filtered(
        source=source, search=search, start_date=start_dt, end_date=end_dt, limit=limit
    )

    # Build RSS feed
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "News Feed"
    ET.SubElement(channel, "link").text = f"{domain}/rss"
    ET.SubElement(channel, "description").text = "Latest aggregated news"
    ET.SubElement(channel, "language").text = "en-us"

    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "description").text = article["summary"] or ""
        ET.SubElement(item, "link").text = article["source"]
        ET.SubElement(item, "guid").text = article["source"]
        ET.SubElement(item, "pubDate").text = article["created_at"].strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    xml_str = ET.tostring(rss, encoding="utf-8")
    return Response(content=xml_str, media_type="application/rss+xml")
