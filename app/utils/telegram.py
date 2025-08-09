import os
import re
import requests
import warnings
from urllib.parse import urlparse
from bs4 import BeautifulSoup


# Get default chat IDs from environment
english_default_chat_id = os.getenv("ENGLISH_CHANNEL_ID")
farsi_default_chat_id = os.getenv("FARSI_CHANNEL_ID")

if not english_default_chat_id:
    raise RuntimeError("ENGLISH_CHANNEL_ID environment variable is not set.")
if not farsi_default_chat_id:
    raise RuntimeError("FARSI_CHANNEL_ID environment variable is not set.")


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


def format_article_md2(title, summary, sources, tag, locale="english"):
    """
    Formats a single article to Telegram MarkdownV2 format.
    Ensures sources are clickable links.

    Args:
        title (str): Article title
        summary (str): Article summary
        sources (list): List of source URLs
        tag (str): Topic tag
        locale (str): Language locale ('english' or 'farsi')
    """
    title = escape_markdown_v2(title)
    summary = escape_markdown_v2(summary)
    tag = escape_markdown_v2(f"#{tag}")

    # Normalize sources into a list
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

    # Format based on locale
    if locale == "farsi":
        return (
            f"*{title}*\n\n"
            f"*خلاصه:* {summary}\n\n"
            f"*منبع:* {sources_text}\n\n"
            f"{tag}"
        )
    else:  # Default to English
        return (
            f"*{title}*\n\n"
            f"*Summary:* {summary}\n\n"
            f"*Source:* {sources_text}\n\n"
            f"{tag}"
        )


def send_to_telegram(headline, topic, locale="english", chat_id=None):
    """
    Sends a formatted article to a Telegram chat.
    Optionally includes one image if found from the first source link.

    Args:
        headline (dict): Article dictionary with title, summary, sources, and optional Farsi fields
        topic (str): Topic tag for the article
        locale (str): Language locale ('english' or 'farsi'), defaults to 'english'
        chat_id (int, optional): Telegram chat ID. If not provided, uses default based on locale
    """
    # Validate and normalize locale
    supported_locales = ["english", "farsi"]
    if locale not in supported_locales:
        warnings.warn(f"Unsupported locale '{locale}'. Using default 'english'.")
        locale = "english"

    # Set default chat_id based on locale if not provided
    if chat_id is None:
        chat_id = farsi_default_chat_id if locale == "farsi" else english_default_chat_id
        chat_id = int(chat_id)  # Ensure it's an integer

    # Extract fields based on locale
    if locale == "farsi":
        title = headline.get("farsi_title", headline.get("title", ""))
        summary = headline.get("farsi_summary", headline.get("summary", ""))
        if not title or not summary:
            warnings.warn(
                "Farsi fields not found in headline. Falling back to English."
            )
            title = headline.get("title", "")
            summary = headline.get("summary", "")
            locale = "english"  # Switch to English formatting
            # Update chat_id to English default when falling back
            chat_id = int(english_default_chat_id)
    else:
        title = headline.get("title", "")
        summary = headline.get("summary", "")

    sources = headline.get("sources", [])

    bot_token = os.environ.get("TELEGRAM_TOKEN")
    if not bot_token:
        raise RuntimeError("TELEGRAM_TOKEN environment variable is not set.")
    
    final_text = format_article_md2(title, summary, sources, tag=topic, locale=locale)

    # Normalize sources to list format
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
            "disable_web_page_preview": True,
        }
        return requests.post(f"{url}/sendPhoto", data=payload)
    else:
        # Send text message
        payload = {
            "chat_id": chat_id,
            "text": final_text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        }
        return requests.post(f"{url}/sendMessage", data=payload)