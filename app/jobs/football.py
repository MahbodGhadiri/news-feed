from app.jobs.base import AbstractCronJob
from app.db.article_service import ArticleService
from app.utils.football_data import FootballDataClient
from app.utils.ai import GeminiClient
from app.utils.telegram import send_to_telegram


class FootballWeekSummary(AbstractCronJob):
    def __init__(
        self,
        article_service: ArticleService,
        cron_expression: str,
        job_name: str,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = "football_upcoming_week"
        self.article_service = article_service

    def run(self):
        """
        Synchronous run method for thread execution
        """
        football_client = FootballDataClient()
        summary_inputs = football_client.prep_next_week_summary()

        llm_client = GeminiClient(
            system_instruction=[
                "You will receive a list of games and standings for a competition",
                "Your task is to summarize it for a Telegram audience using a clear and concise format.",
                "Use informative section headers with relevant emojis to improve readability. Also add new line after each section you write to keep the readability high",
                "Ensure the summary is well-structured and not overly long.",
                """ 
                You will receive match data, including home team, away team, date, and standings. 
                Use the following ranking scale with short names and emojis:

                Level 5 – Legendary 🔥🔥 → The absolute peak, historic rivalries, finals, title deciders.  
                Level 4 – Firestorm 🔥 → Explosive encounters with guaranteed thrills.  
                Level 3 – Sizzle 🌶️ → High-energy games likely to deliver plenty of moments.  
                Level 2 – Warm 🌡️ → Solid football, worth watching if you have time.  
                Level 1 – Chill 🥱 → Only for die-hard fans or followers of these clubs.  

                Rules for assigning levels:
                - Always display the local Tehran time (from `tehran_date_shamsi` in farsi and `tehran_date_gregorian` in english).
                - No more than **one Level 5** match per competition summary.  
                - No more than **two Level 4** matches per competition summary.  
                - Keep the top 3 levels (5, 4, and 3) limited and selective so they highlight only the most important games.  
                - Level 2 and Level 1 should be used more broadly to cover the rest of the matches.  

                For each match:
                1. Select the correct ranking level based on standings, rivalry, and stakes.
                2. Output in the following format:

                [Rank Name] [Emoji] | {Home Team} 🆚 {Away Team}  
                📅 Date: {Date in DD MMM YYYY format}  
                📊 Standing Snapshot: "{Home Standing} vs {Away Standing} – short context"  
                💡 Why Watch: {One-line hype statement}  
                """,
                """
                the farsi ranking level is as follows: 
                سطح ۵ – نبرد افسانه‌ای 🔥🔥
                بازی‌هایی که تاریخ را می‌سازند؛ فینال‌ها، دربی‌های بزرگ، و جدال‌های قهرمانی.

                سطح ۴ – بازی آتشین 🔥
                برخورد پرشور و تماشایی با هیجان تضمینی.

                سطح ۳ – رویارویی داغ 🌶️
                بازی پرانرژی و پرموقعیت با احتمال بالای صحنه‌های تماشایی.

                سطح ۲ – دیدار تماشایی 🌡️
                فوتبال خوب و قابل‌قبول که ارزش پیگیری دارد.

                سطح ۱ – دیدار کم‌حرارت 🥱
                فقط برای هواداران دوآتشه یا طرفداران قدیمی این تیم‌ها.
                """,
                "Your response must be in valid JSON following this format:",
                "- `article`: an object containing:",
                "   - `title`: A concise string (e.g. '[Competition name] upcoming week preview')",
                "   - `farsi_title`: A Farsi translation of the title",
                "   - `summary`: List of games in the mentioned format",
                "   - `farsi_summary`: translation of the summary to farsi, it does not have to be exact translation make sure it has a natural flow to it",
                "All English fields must be clear and suitable for public audiences.",
                "All Farsi fields must be accurate translations maintaining the same meaning and tone.",
            ]
        )

        for summary_input in summary_inputs:
            articles = llm_client.generate(str(summary_input))["articles"]

            if len(articles) == 0:
                continue

            for article in articles:

                if not article:
                    self.logger.info("✅ done - no article generated")
                    continue

                # Create the result dictionary compatible with send_to_telegram
                headline = {
                    "title": article["title"],
                    "farsi_title": article["farsi_title"],
                    "summary": "\n" + article["summary"],
                    "farsi_summary": "\n" + article["farsi_summary"],
                    "sources": [""],
                }

                # Save to database
                self.article_service.create_article(
                    headline["title"],
                    headline["summary"],
                    "",
                    farsi_title=headline["farsi_title"],
                    farsi_summary=headline["farsi_summary"],
                    sent_to_telegram=True,
                )
                # Send to Telegram in both languages
                send_to_telegram(headline, self.topic, locale="english")
                send_to_telegram(headline, self.topic, locale="farsi")

        return True


class FootballYesterdayResults(AbstractCronJob):
    def __init__(
        self,
        article_service: ArticleService,
        cron_expression: str,
        job_name: str,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = "football_upcoming_week"
        self.article_service = article_service

    def run(self):
        """
        Synchronous run method for thread execution
        """
        football_client = FootballDataClient()
        summary_inputs = football_client.prep_last_day_summary()

        llm_client = GeminiClient(
            system_instruction=[
                "You will receive a list of games for a football competition.",
                "Your task is to summarize it for a Telegram audience using a clear and concise format.",
                "Focus on the results of the matches and provide short but engaging recaps.",
                "Use informative section headers with relevant emojis to improve readability. Add a new line after each section you write to keep readability high.",
                "Ensure the summary is well-structured, compact, and not overly long.",
                """
                You will receive match data in the following format:
                {
                'competition': 'PL',
                'matches': [
                    'competition=Premier League|home_team=Aston Villa FC|away_team=Newcastle United FC|utc_date=2025-08-16T11:30:00Z|tehran_date=2025-08-16T15:00:00+03:30|status=finished|score=0-0',
                    ...
                ]
                }

                Rules:
                - Always display the local Tehran time (from `tehran_date_shamsi` in farsi and `tehran_date_gregorian` in english).
                - Ignore the `utc_date` in the output.
                - Use the `score` exactly as provided (format: Home – Away).
                - `status` will be 'finished' → summarize only completed matches.

                For each match, output in this format (with real line breaks, not escaped):
                
                ⚽ {Home Team} {Home Score} – {Away Score} {Away Team}  
                📅 Date: {DD MMM YYYY, HH:MM Tehran time}  
                """,
                "Your response must be in valid JSON following this format:",
                "- `article`: an object containing:",
                "   - `title`: A concise string (e.g. '[Competition name] matchday results - [Date]')",
                "   - `farsi_title`: A Farsi translation of the title",
                "   - `summary`: List of games in the mentioned format (with real line breaks for readability)",
                "   - `farsi_summary`: A natural-sounding translation of the summary to Farsi (does not need to be literal word-for-word, but must flow well in Persian).",
                "All English fields must be clear, concise, and suitable for public audiences.",
                "All Farsi fields must be accurate translations maintaining the same meaning and tone.",
            ]
        )

        for summary_input in summary_inputs:
            articles = llm_client.generate(str(summary_input))["articles"]

            if len(articles) == 0:
                continue

            for article in articles:
                if not article:
                    self.logger.info("✅ done - no article generated")
                    continue

                # Create the result dictionary compatible with send_to_telegram
                headline = {
                    "title": article["title"],
                    "farsi_title": article["farsi_title"],
                    "summary": "\n" + article["summary"],
                    "farsi_summary": "\n" + article["farsi_summary"],
                    "sources": [""],
                }

                # Save to database
                self.article_service.create_article(
                    headline["title"],
                    headline["summary"],
                    "",
                    farsi_title=headline["farsi_title"],
                    farsi_summary=headline["farsi_summary"],
                    sent_to_telegram=True,
                )
                # Send to Telegram in both languages
                send_to_telegram(headline, self.topic, locale="english")
                send_to_telegram(headline, self.topic, locale="farsi")

        return True


class FootballTodayGameNotification(AbstractCronJob):
    def __init__(
        self,
        article_service: ArticleService,
        cron_expression: str,
        job_name: str,
    ):
        super().__init__(cron_expression, job_name)
        self.topic = "football_upcoming_week"
        self.article_service = article_service

    def run(self):
        """
        Synchronous run method for thread execution
        """
        football_client = FootballDataClient()
        summary_inputs = football_client.prep_today_summary()

        llm_client = GeminiClient(
            system_instruction=[
                "You will receive a list of games for a football competition.",
                "Your task is to summarize it for a Telegram audience using a clear and concise format.",
                "Focus on notifying users of today's games with the local Tehran kickoff times.",
                "Use informative section headers with relevant emojis to improve readability. Add a new line after each section you write to keep readability high.",
                "Ensure the summary is well-structured, compact, and not overly long.",
                """
            You will receive match data in the following format:
            {
            'competition': 'PL',
            'matches': [
                'competition=Premier League|home_team=Aston Villa FC|away_team=Newcastle United FC|utc_date=2025-08-16T11:30:00Z|tehran_date=2025-08-16T15:00:00+03:30|status=scheduled',
                ...
            ]
            }

            Rules:
            - Always display the local Tehran time (from `tehran_date_shamsi` in farsi and `tehran_date_gregorian` in english).
            - Ignore the `utc_date` in the output.
            - Do not display scores (since matches have not started).
            - `status` will be 'scheduled' → only show matches happening today.

            For each match, output in this format (with real line breaks, not escaped):
            
            ⚽ {Home Team} 🆚 {Away Team}  
            🕒 Kickoff: {DD MMM YYYY, HH:MM Tehran time}  
            """,
                "Your response must be in valid JSON following this format:",
                "- `article`: an object containing:",
                "   - `title`: A concise string (e.g. '[Competition name] today’s matches - [Date]')",
                "   - `farsi_title`: A Farsi translation of the title",
                "   - `summary`: List of games in the mentioned format (with real line breaks for readability)",
                "   - `farsi_summary`: A natural-sounding translation of the summary to Farsi (does not need to be literal word-for-word, but must flow well in Persian).",
                "All English fields must be clear, concise, and suitable for public audiences.",
                "All Farsi fields must be accurate translations maintaining the same meaning and tone.",
            ]
        )

        for summary_input in summary_inputs:
            articles = llm_client.generate(str(summary_input))["articles"]

            if len(articles) == 0:
                continue

            for article in articles:
                if not article:
                    self.logger.info("✅ done - no article generated")
                    continue

                # Create the result dictionary compatible with send_to_telegram
                headline = {
                    "title": article["title"],
                    "farsi_title": article["farsi_title"],
                    "summary": "\n" + article["summary"],
                    "farsi_summary": "\n" + article["farsi_summary"],
                    "sources": [""],
                }

                # Save to database
                self.article_service.create_article(
                    headline["title"],
                    headline["summary"],
                    "",
                    farsi_title=headline["farsi_title"],
                    farsi_summary=headline["farsi_summary"],
                    sent_to_telegram=True,
                )
                # Send to Telegram in both languages
                send_to_telegram(headline, self.topic, locale="english")
                send_to_telegram(headline, self.topic, locale="farsi")

        return True
