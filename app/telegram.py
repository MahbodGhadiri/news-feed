import requests
import os

import re

def escape_markdown_v2(text):
    """
    Escapes special characters for Telegram MarkdownV2 format.
    """
    special_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(rf"([{re.escape(special_chars)}])", r"\\\1", text)

def format_article_md2(headline, tag):
    """Formats a single article dictionary to Telegram MarkdownV2 format."""
    title = escape_markdown_v2(headline["title"])
    summary = escape_markdown_v2(headline["summary"])
    tag = escape_markdown_v2(f"#{tag}")
    
    # Handle one or more sources (list or single string)
    sources = headline.get("sources", [])
    if isinstance(sources, str):
        sources = [sources]

    # Format sources as links if possible
    formatted_sources = []
    for url in sources:
        safe_url = url.replace(")", "%29").replace("(", "%28")  # optional URL safety
        label = escape_markdown_v2(url)
        formatted_sources.append(f"[{label}]({safe_url})")

    sources_text = ", ".join(formatted_sources)

    return f"""
*{title}* 

*Summary:* {summary}

*Source:* {sources_text}

 {tag}
"""


def send_to_telegram(headline, topic, chat_id=-1002621988066):
    bot_token = os.environ.get("TELEGRAM_TOKEN")


    final_text = format_article_md2(headline, tag=topic)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": final_text,
        "parse_mode": "MarkdownV2"  # or "MarkdownV2" if you want formatting
    }
    response = requests.post(url, data=payload)
    return response
