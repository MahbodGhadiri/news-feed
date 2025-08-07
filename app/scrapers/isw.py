from bs4 import BeautifulSoup
import json
import re
import requests
from datetime import datetime, timedelta


class ISWReportScraper:
    BASE_URL = "https://www.understandingwar.org/backgrounder/russian-offensive-campaign-assessment-{}"

    def __init__(self, date=None):
        self.date_obj = date or (datetime.today() - timedelta(days=1))
        self.formatted_date = self.date_obj.strftime(
            "%B-%-d-%Y"
        ).lower()  # e.g. august-6-2025
        self.url = self.BASE_URL.format(self.formatted_date)
        self.soup = None
        self.report_data = {}

    def fetch_page(self):
        res = requests.get(self.url)
        if res.status_code != 200:
            raise Exception(f"Failed to fetch page: {res.status_code}\n{res.text}")
        self.soup = BeautifulSoup(res.text, "html.parser")

    def get_text_safe(self, tag, default=None):
        return tag.get_text(strip=True) if tag else default

    def get_attr_safe(self, tag, attr, default=None):
        return tag.get(attr) if tag and tag.has_attr(attr) else default

    def extract_metadata(self):
        self.report_data["title"] = self.get_text_safe(
            self.soup.find("h1", {"id": "page-title"})
        )
        self.report_data["date"] = self.get_attr_safe(
            self.soup.find("span", {"property": "dc:date dc:created"}), "content"
        )
        self.report_data["author"] = self.get_text_safe(
            self.soup.find("a", {"property": "foaf:name"})
        )
        self.report_data["pdf_url"] = self.get_attr_safe(
            self.soup.select_one(".field-name-field-pdf-report a"), "href"
        )
        self.report_data["cover_image"] = self.get_attr_safe(
            self.soup.select_one(".field-name-field-cover-image img"), "src"
        )

    def extract_sections(self):
        body_div = self.soup.select_one(".field-name-body .field-item")
        body_html = str(body_div) if body_div else ""
        soup_body = BeautifulSoup(body_html, "html.parser")

        sections = []
        current_section = {"title": None, "paragraphs": []}

        for element in soup_body.find_all(["h1", "h2", "h3", "strong", "p"]):
            tag = element.name
            text = element.get_text(strip=True)
            if not text:
                continue

            if tag in ["h1", "h2", "h3", "strong"]:
                if current_section["paragraphs"]:
                    sections.append(current_section)
                current_section = {"title": text, "paragraphs": []}
            elif tag == "p":
                clean_p = re.sub(r"\s+", " ", text.strip())
                if clean_p:
                    current_section["paragraphs"].append(clean_p)

        if current_section["paragraphs"]:
            sections.append(current_section)

        self.report_data["sections"] = self.clean_sections(sections)

    def clean_sections(self, sections):
        cleaned_sections = []
        seen_titles = set()

        for sec in sections:
            title_clean = (
                re.sub(r"\s+", " ", sec["title"].strip())
                if sec["title"]
                else "Untitled Section"
            )
            title_key = title_clean.lower()

            if title_key in seen_titles:
                continue

            paragraphs = [
                re.sub(r"\s+", " ", p.strip()) for p in sec["paragraphs"] if p.strip()
            ]
            if not paragraphs:
                continue

            seen_titles.add(title_key)
            cleaned_sections.append({"title": title_clean, "paragraphs": paragraphs})

        if cleaned_sections:
            cleaned_sections.pop()  # Remove the last section
        return cleaned_sections

    def save_to_json(self, path="report_data.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        print("✅ report_data.json generated successfully.")

    def prep_summary(self):
        summary_lines = []

        summary_lines.append(f"📰 Title: {self.report_data.get('title', 'N/A')}")
        summary_lines.append(f"📅 Date: {self.report_data.get('date', 'N/A')}")
        summary_lines.append(f"✍️ Author: {self.report_data.get('author', 'N/A')}")

        if self.report_data.get("pdf_url"):
            summary_lines.append(f"📄 PDF Report: {self.report_data['pdf_url']}")
        if self.report_data.get("cover_image"):
            summary_lines.append(f"🖼️ Cover Image: {self.report_data['cover_image']}")

        summary_lines.append("\n📚 Sections:\n")

        for section in self.report_data.get("sections", []):
            summary_lines.append(f"🔹 {section['title']}")
            for para in section["paragraphs"][
                :2
            ]:  # show only first 2 paragraphs as preview
                summary_lines.append(f"   - {para}")
            if len(section["paragraphs"]) > 2:
                summary_lines.append(
                    f"   ...({len(section['paragraphs']) - 2} more paragraph(s))\n"
                )
            else:
                summary_lines.append("")

        return "\n".join(summary_lines)

    def run(self):
        self.fetch_page()
        self.extract_metadata()
        self.extract_sections()
        return self.prep_summary()
