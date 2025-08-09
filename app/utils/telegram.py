import os
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def escape_markdown_v2(text):
    """
    Escapes special characters for Telegram MarkdownV2 format.
    """
    special_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(rf"([{re.escape(special_chars)}])", r"\\\1", text)


def extract_image_from_url(url):
    """
    Attempts to extract the first image from the page using Open Graph tags.
    Returns image URL or None.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for Open Graph image
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"]
        
        # Fallback: try Twitter card image
        twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_img and twitter_img.get("content"):
            return twitter_img["content"]

    except requests.RequestException:
        pass

    return None


def format_article_md2(headline, tag):
    """
    Formats a single article dictionary to Telegram MarkdownV2 format.
    Ensures sources are clickable links.
    """
    title = escape_markdown_v2(headline["title"])
    summary = escape_markdown_v2(headline["summary"])
    tag = escape_markdown_v2(f"#{tag}")

    # Normalize sources into a list
    sources = headline.get("sources", [])
    if isinstance(sources, str):
        sources = [sources]

    # Format sources as clickable links
    formatted_sources = []

    for url in sources:
        safe_url = url.replace(")", "%29").replace("(", "%28")
        domain = urlparse(url).netloc  # e.g., 'www.bbc.com'
        domain_label = domain.replace("www.", "")  # optional: remove 'www.'
        label = escape_markdown_v2(domain_label)
        formatted_sources.append(f"[{label}]({safe_url})")


    sources_text = ", ".join(formatted_sources)

    return (
        f"*{title}*\n\n"
        f"*Summary:* {summary}\n\n"
        f"*Source:* {sources_text}\n\n"
        f"{tag}"
    )


def send_to_telegram(headline, topic, chat_id=-1002621988066):
    """
    Sends a formatted article to a Telegram chat.
    Optionally includes one image if found from the first source link.
    """
    bot_token = os.environ.get("TELEGRAM_TOKEN")
    final_text = format_article_md2(headline, tag=topic)

    # Try to get an image from the first source (if any)
    sources = headline.get("sources", [])
    if isinstance(sources, str):
        sources = [sources]

    image_url = None
    if sources:
        image_url = extract_image_from_url(sources[0])

    url = f"https://api.telegram.org/bot{bot_token}"
    if image_url:
        # Send image with caption
        payload = {
            "chat_id": chat_id,
            "caption": final_text,
            "parse_mode": "MarkdownV2",
            "photo": image_url,
            "disable_web_page_preview": True
        }
        return requests.post(f"{url}/sendPhoto", data=payload)
    else:
        # Send normal text message
        payload = {
            "chat_id": chat_id,
            "text": final_text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }
        return requests.post(f"{url}/sendMessage", data=payload)
