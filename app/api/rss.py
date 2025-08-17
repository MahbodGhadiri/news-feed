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


def build_rss_feed(articles, domain, locale="english"):
    """
    Builds RSS feed XML for given articles and locale with proper encoding
    """
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    if locale == "farsi":
        ET.SubElement(channel, "title").text = "اخبار مهبد"
        ET.SubElement(channel, "link").text = f"{domain}/rss/farsi"
        ET.SubElement(channel, "description").text = "آخرین اخبار از منابع معتبر شما"
        ET.SubElement(channel, "language").text = "fa-ir"
    else:  # English
        ET.SubElement(channel, "title").text = "Mahbod's News Feed"
        ET.SubElement(channel, "link").text = f"{domain}/rss"
        ET.SubElement(channel, "description").text = (
            "Latest news by your trusted sources"
        )
        ET.SubElement(channel, "language").text = "en-us"

    for article in articles:
        # Skip articles that don't have content for the requested locale
        if locale == "farsi":
            title = article.get("farsi_title")
            summary = article.get("farsi_summary")
            # Skip if no Farsi content available
            if not title or not summary:
                continue
        else:  # English
            title = article["title"]
            summary = article["summary"]
            # Skip if no English content (shouldn't happen, but safety check)
            if not title:
                continue

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "description").text = summary or ""
        ET.SubElement(item, "link").text = article["source"]
        ET.SubElement(item, "guid").text = article["source"]
        ET.SubElement(item, "pubDate").text = article["created_at"].strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    # Return as string with proper UTF-8 encoding declaration
    xml_str = ET.tostring(rss, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


@router.get("/rss", response_class=Response)
def get_rss(
    source: Optional[str] = Query(None, description="Filter by source URL"),
    search: Optional[str] = Query(None, description="Search in title or summary"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Limit number of articles"),
):
    """
    English RSS feed - maintains existing URL for backward compatibility
    """
    domain = os.environ.get("SERVER_URL")

    # Parse dates if provided
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # Fetch filtered articles
    articles = article_service.list_articles_filtered(
        source=source, search=search, start_date=start_dt, end_date=end_dt, limit=limit
    )

    xml_str = build_rss_feed(articles, domain, locale="english")
    return Response(
        content=xml_str,
        media_type="application/rss+xml; charset=utf-8",
        headers={"Content-Type": "application/rss+xml; charset=utf-8"},
    )


@router.get("/rss/farsi", response_class=Response)
def get_rss_farsi(
    source: Optional[str] = Query(None, description="Filter by source URL"),
    search: Optional[str] = Query(None, description="Search in title or summary"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Limit number of articles"),
):
    """
    Farsi RSS feed - separate endpoint for Persian content
    """
    domain = os.environ.get("SERVER_URL")

    # Parse dates if provided
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # Fetch filtered articles
    articles = article_service.list_articles_filtered(
        source=source, search=search, start_date=start_dt, end_date=end_dt, limit=limit
    )

    xml_str = build_rss_feed(articles, domain, locale="farsi")
    return Response(
        content=xml_str,
        media_type="application/rss+xml; charset=utf-8",
        headers={"Content-Type": "application/rss+xml; charset=utf-8"},
    )
