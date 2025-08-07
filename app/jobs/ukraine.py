from app.jobs.base import AbstractCronJob
from app.scrapers.isw import ISWReportScraper
from app.ai import GeminiClient
from app.telegram import send_to_telegram
from google.genai import types


class UkraineSummary(AbstractCronJob):
    def __init__(
        self,
        cron_expression: str,
        job_name: str,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = "ukraine_war_daily_update"

    async def run(self):
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
                "   - `body`: An object with the following fields:",
                "       • `political_developments`: string",
                "       • `economical_developments`: string",
                "       • `air_war`: string",
                "       • `changes_on_ground`: string",
                "       • `other` (optional): string for miscellaneous updates",
                "   - `source`: Always set to 'ISW'",
                "All fields must be in English. Keep language clear and suitable for public audiences.",
            ],
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                required=["article"],
                properties={
                    "article": types.Schema(
                        type=types.Type.OBJECT,
                        required=["title", "body", "source"],
                        properties={
                            "title": types.Schema(type=types.Type.STRING),
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
                            "source": types.Schema(type=types.Type.STRING),
                        },
                    )
                },
            ),
        )
        article = llm_client.generate(summary_input)["article"]

        if not article:
            return

        body_sections = []
        for section_name, content in article["body"].items():
            body_sections.append(content)

        # Create the result dictionary
        headline = {
            "title": article["title"],
            "sources": [article["source"]],
            "summary": "\n" + "\n\n".join(body_sections),
        }
        send_to_telegram(headline, self.topic)
