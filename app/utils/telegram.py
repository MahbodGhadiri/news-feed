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

# Telegram message length limit
TELEGRAM_MAX_LENGTH = 4096


def escape_markdown_v2(text):
    """
    Escapes special characters for Telegram MarkdownV2 format.
    """
    special_chars = r"_[]()~`>#+-=|{}.!\\"
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


def split_text_intelligently(text):
    """
    Splits text intelligently by paragraphs, then sentences if needed.
    Returns list of text chunks.
    """
    # First try splitting by double newlines (paragraphs)
    paragraphs = text.split("\n\n")

    if len(paragraphs) > 1:
        return paragraphs

    # If no double newlines, try single newlines
    lines = text.split("\n")

    if len(lines) > 1:
        return lines

    # If no newlines, split by sentences
    # Use regex to split on sentence endings while preserving the punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_summary(summary, max_chunk_size=3000):
    """
    Chunks the summary into smaller pieces that fit within Telegram limits.
    Leaves room for title, source, and formatting.
    """
    if len(summary) <= max_chunk_size:
        return [summary]

    chunks = []
    text_parts = split_text_intelligently(summary)

    current_chunk = ""

    for part in text_parts:
        # Check if adding this part would exceed the limit
        test_chunk = current_chunk + ("\n\n" if current_chunk else "") + part

        if len(test_chunk) <= max_chunk_size:
            current_chunk = test_chunk
        else:
            # If current_chunk has content, save it and start new chunk
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = part
            else:
                # Single part is too long, need to split it further
                # Split by sentences if it's a paragraph, or by words as last resort
                if len(part) > max_chunk_size:
                    sub_parts = split_text_intelligently(part)
                    for sub_part in sub_parts:
                        if len(sub_part) <= max_chunk_size:
                            if (
                                current_chunk
                                and len(current_chunk + "\n\n" + sub_part)
                                <= max_chunk_size
                            ):
                                current_chunk += "\n\n" + sub_part
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)
                                current_chunk = sub_part
                        else:
                            # Last resort: split by words
                            words = sub_part.split()
                            temp_chunk = ""
                            for word in words:
                                test_temp = (
                                    temp_chunk + (" " if temp_chunk else "") + word
                                )
                                if len(test_temp) <= max_chunk_size:
                                    temp_chunk = test_temp
                                else:
                                    if temp_chunk:
                                        if current_chunk:
                                            chunks.append(current_chunk)
                                            current_chunk = ""
                                        chunks.append(temp_chunk)
                                    temp_chunk = word

                            if temp_chunk:
                                if (
                                    current_chunk
                                    and len(current_chunk + " " + temp_chunk)
                                    <= max_chunk_size
                                ):
                                    current_chunk += " " + temp_chunk
                                else:
                                    if current_chunk:
                                        chunks.append(current_chunk)
                                    current_chunk = temp_chunk
                else:
                    current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_article_md2(title, summary, sources, tag, locale="english"):
    """
    Formats articles to Telegram MarkdownV2 format, splitting into multiple messages if needed.
    Returns a list of formatted messages.

    Args:
        title (str): Article title
        summary (str): Article summary
        sources (list): List of source URLs
        tag (str): Topic tag
        locale (str): Language locale ('english' or 'farsi')
    """
    escaped_title = escape_markdown_v2(title)
    escaped_tag = escape_markdown_v2(f"#{tag}")

    # Normalize sources into a list
    if isinstance(sources, str):
        sources = [sources]

    # Format sources as clickable links
    formatted_sources = []
    for url in sources:
        safe_url = url.replace(")", "%29").replace("(", "%28")
        domain = urlparse(url).netloc
        domain_label = domain.replace("www.", "")
        label = escape_markdown_v2(domain_label)
        formatted_sources.append(f"[{label}]({safe_url})")

    sources_text = ", ".join(formatted_sources)

    # Prepare source section based on locale
    if locale == "farsi":
        source_section = f"*منبع:* {sources_text}\n\n{escaped_tag}"
        summary_label = "*خلاصه:*"
    else:
        source_section = f"*Source:* {sources_text}\n\n{escaped_tag}"
        summary_label = "*Summary:*"

    # Calculate available space for summary
    title_section = f"*{escaped_title}*\n\n"
    base_message_size = (
        len(title_section) + len(source_section) + len(f"{summary_label} ") + 50
    )  # buffer
    max_summary_size = TELEGRAM_MAX_LENGTH - base_message_size

    # Check if we need to split
    if len(summary) <= max_summary_size:
        # Single message
        escaped_summary = escape_markdown_v2(summary)
        message = (
            f"{title_section}{summary_label} {escaped_summary}\n\n{source_section}"
        )
        return [message]

    # Multiple messages needed
    summary_chunks = chunk_summary(summary, max_summary_size)
    messages = []

    for i, chunk in enumerate(summary_chunks, 1):
        escaped_chunk = escape_markdown_v2(chunk)

        # Add part number to title for multi-part messages
        if len(summary_chunks) > 1:
            part_word = "بخش" if locale == "farsi" else "Part"
            part_title = f"{title} ({part_word} {i})"
        else:
            part_title = title
        title_section = f"*{escape_markdown_v2(part_title)}*\n\n"

        if i == len(summary_chunks):
            # Last message includes sources
            message = (
                f"{title_section}{summary_label} {escaped_chunk}\n\n{source_section}"
            )
        else:
            # Intermediate messages without sources
            message = f"{title_section}{summary_label} {escaped_chunk}"

        messages.append(message)

    return messages


def send_to_telegram(headline, topic, locale="english", chat_id=None):
    """
    Sends formatted article(s) to a Telegram chat.
    Handles message splitting automatically.

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
        chat_id = (
            farsi_default_chat_id if locale == "farsi" else english_default_chat_id
        )
        chat_id = int(chat_id)

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
            locale = "english"
            chat_id = int(english_default_chat_id)
    else:
        title = headline.get("title", "")
        summary = headline.get("summary", "")

    sources = headline.get("sources", [])

    bot_token = os.environ.get("TELEGRAM_TOKEN")
    if not bot_token:
        raise RuntimeError("TELEGRAM_TOKEN environment variable is not set.")

    # Get formatted messages (could be multiple)
    messages = format_article_md2(title, summary, sources, tag=topic, locale=locale)

    # Normalize sources to list format for image extraction
    if isinstance(sources, str):
        sources = [sources]

    image_url = None
    if sources:
        image_url = extract_image_from_url(sources[0])

    url = f"https://api.telegram.org/bot{bot_token}"
    responses = []

    for i, message in enumerate(messages):
        if i == 0 and image_url:
            # Send first message with image
            payload = {
                "chat_id": chat_id,
                "caption": message,
                "parse_mode": "MarkdownV2",
                "photo": image_url,
                "disable_web_page_preview": True,
            }
            response = requests.post(f"{url}/sendPhoto", data=payload)
        else:
            # Send text message
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            }
            response = requests.post(f"{url}/sendMessage", data=payload)

        responses.append(response)

    return responses  # Returns list of responses for all sent messages
