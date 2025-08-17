from app.jobs.base import AbstractCronJob
from app.db.article_service import ArticleService
from app.scrapers.isw import ISWReportScraper
from app.utils.ai import GeminiClient
from app.utils.telegram import send_to_telegram
from google.genai import types


class UkraineSummary(AbstractCronJob):
    def __init__(
        self,
        article_service: ArticleService,
        cron_expression: str,
        job_name: str,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = "ukraine_war_daily_update"
        self.article_service = article_service

    def run(self):
        """
        Synchronous run method for thread execution
        """
        scraper = ISWReportScraper()
        summary_input = scraper.run()

        llm_client = GeminiClient(
            system_instruction=[
                "You will receive a single ISW (Institute for the Study of War) report.",
                "Your task is to summarize it for a Telegram audience using a clear and concise format.",
                "Use informative section headers with relevant emojis to improve readability. Also add new line when required.",
                "Use only the information from the provided article — do not invent or add external context.",
                "Ensure the summary is well-structured and not overly long.",
                "Your response must be in valid JSON following this format:",
                "- `article`: an object containing:",
                "   - `title`: A concise string (e.g. 'Ukraine Update – MMM DD, YYYY')",
                "   - `farsi_title`: A Farsi translation of the title",
                "   - `body`: An object with the following fields:",
                "       • `political_developments`: string",
                "       • `economical_developments`: string",
                "       • `air_war`: string",
                "       • `changes_on_ground`: string",
                "       • `other` (optional): string for miscellaneous updates",
                "   - `farsi_body`: An object with Farsi translations of the body fields:",
                "       • `political_developments`: string",
                "       • `economical_developments`: string",
                "       • `air_war`: string",
                "       • `changes_on_ground`: string",
                "       • `other` (optional): string for miscellaneous updates",
                "All English fields must be clear and suitable for public audiences.",
                "All Farsi fields must be accurate translations maintaining the same meaning and tone.",
            ],
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                required=["article"],
                properties={
                    "article": types.Schema(
                        type=types.Type.OBJECT,
                        required=["title", "farsi_title", "body", "farsi_body"],
                        properties={
                            "title": types.Schema(type=types.Type.STRING),
                            "farsi_title": types.Schema(type=types.Type.STRING),
                            "body": types.Schema(
                                type=types.Type.OBJECT,
                                required=[
                                    "political_developments",
                                    "economical_developments",
                                    "air_war",
                                    "changes_on_ground",
                                ],
                                properties={
                                    "political_developments": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "economical_developments": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "air_war": types.Schema(type=types.Type.STRING),
                                    "changes_on_ground": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "other": types.Schema(type=types.Type.STRING),
                                },
                            ),
                            "farsi_body": types.Schema(
                                type=types.Type.OBJECT,
                                required=[
                                    "political_developments",
                                    "economical_developments",
                                    "air_war",
                                    "changes_on_ground",
                                ],
                                properties={
                                    "political_developments": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "economical_developments": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "air_war": types.Schema(type=types.Type.STRING),
                                    "changes_on_ground": types.Schema(
                                        type=types.Type.STRING
                                    ),
                                    "other": types.Schema(type=types.Type.STRING),
                                },
                            ),
                        },
                    )
                },
            ),
        )

        article = llm_client.generate(summary_input)["article"]

        if not article:
            self.logger.info("✅ done - no article generated")
            return True

        # Build English summary from body sections
        english_body_sections = []
        for _, content in article["body"].items():
            if content:  # Only add non-empty sections
                english_body_sections.append(content)

        # Build Farsi summary from farsi_body sections
        farsi_body_sections = []
        for _, content in article["farsi_body"].items():
            if content:  # Only add non-empty sections
                farsi_body_sections.append(content)

        # Create the result dictionary compatible with send_to_telegram
        headline = {
            "title": article["title"],
            "farsi_title": article["farsi_title"],
            "summary": "\n" + "\n\n".join(english_body_sections),
            "farsi_summary": "\n" + "\n\n".join(farsi_body_sections),
            "sources": [scraper.get_source()],
        }

        # Save to database
        self.article_service.create_article(
            headline["title"],
            headline["summary"],
            scraper.get_source(),
            farsi_title=headline["farsi_title"],
            farsi_summary=headline["farsi_summary"],
            sent_to_telegram=True,
        )

        # Send to Telegram in both languages
        send_to_telegram(headline, self.topic, locale="english")
        send_to_telegram(headline, self.topic, locale="farsi")

        self.logger.info(f"✅ Task Ended - aggregated {self.topic} news")
        return True
