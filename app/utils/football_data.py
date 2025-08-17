import os
import requests
from datetime import datetime, timedelta
import pytz
import jdatetime
from app.utils.logger import setup_logger

from dotenv import load_dotenv

load_dotenv()


class FootballDataClient:
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, competitions=None):
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        if not self.api_key:
            raise ValueError("FOOTBALL_API_KEY environment variable not found")

        self.headers = {"X-Auth-Token": self.api_key}
        self.competitions = competitions or ["PL", "PD", "BL1", "CL"]
        self.logger = setup_logger(self.__class__.__name__)

    def get_matches_for_competition(self, competition_code, date_from, date_to):
        """Fetch matches for a competition in a given date range."""
        url = f"{self.BASE_URL}/competitions/{competition_code}/matches"
        params = {"dateFrom": date_from, "dateTo": date_to}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("matches", [])

    def get_standings_for_competition(self, competition_code):
        """Fetch current standings for a competition."""
        url = f"{self.BASE_URL}/competitions/{competition_code}/standings"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        standings = []
        for table in data.get("standings", []):
            if table["type"] == "TOTAL":
                for entry in table["table"]:
                    standings.append(
                        {
                            "competition": data.get("competition", {}).get(
                                "name", competition_code
                            ),
                            "position": entry["position"],
                            "team": entry["team"]["name"],
                            "played": entry["playedGames"],
                            "won": entry["won"],
                            "draw": entry["draw"],
                            "lost": entry["lost"],
                            "points": entry["points"],
                            "goal_difference": entry["goalDifference"],
                        }
                    )
        return standings

    def get_next_week_date_range(self, start_date=None):
        """Get start and end dates of next week (Friday to Thursday)."""
        if start_date is None:
            start_date = datetime.now()

        # Find current Friday (start of week)
        days_since_friday = (start_date.weekday() - 4) % 7
        current_friday = start_date - timedelta(days=days_since_friday)

        # Next week starts 7 days later
        next_friday = current_friday + timedelta(days=7)
        next_thursday = next_friday + timedelta(days=6)

        return next_friday.date().isoformat(), next_thursday.date().isoformat()

    def format_match_for_llm(self, match):
        """Format match data for LLM consumption."""
        status_map = {
            "SCHEDULED": "scheduled",
            "TIMED": "scheduled",
            "IN_PLAY": "live",
            "PAUSED": "live",
            "FINISHED": "finished",
        }

        competition = match.get("competition", {}).get("name", "Unknown")
        home_team = match["homeTeam"]["name"]
        away_team = match["awayTeam"]["name"]
        utc_date = match["utcDate"]
        status = status_map.get(match.get("status", "UNKNOWN"), "unknown")
        home_score = match["score"]["fullTime"]["home"]
        away_score = match["score"]["fullTime"]["away"]

        # Convert UTC to Tehran time
        utc_dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        tehran_tz = pytz.timezone("Asia/Tehran")
        tehran_dt = utc_dt.astimezone(tehran_tz)

        jalali_dt = jdatetime.datetime.fromgregorian(datetime=tehran_dt)

        tehran_date_gregorian = tehran_dt.isoformat()
        tehran_date_shamsi = jalali_dt.strftime("%Y-%m-%d %H:%M:%S")

        return (
            f"competition={competition}|home_team={home_team}|away_team={away_team}|"
            f"utc_date={utc_date}|tehran_date_shamsi={tehran_date_shamsi}|tehran_date_gregorian={tehran_date_gregorian}|status={status}|"
            f"score={home_score}-{away_score}"
        )

    def format_standings_for_llm(self, standings):
        """Format standings data for LLM consumption."""
        formatted = []
        for standing in standings:
            formatted.append(
                f"competition={standing['competition']}|position={standing['position']}|"
                f"team={standing['team']}|played={standing['played']}|won={standing['won']}|"
                f"draw={standing['draw']}|lost={standing['lost']}|points={standing['points']}|"
                f"goal_difference={standing['goal_difference']}"
            )
        return formatted

    def prep_next_week_summary(self):
        """Generate LLM-friendly summary of next week's matches and current standings."""
        start_date, end_date = self.get_next_week_date_range()
        summaries = []

        for competition in self.competitions:
            try:
                standings = self.get_standings_for_competition(competition)
                matches = self.get_matches_for_competition(
                    competition, start_date, end_date
                )

                if not matches:
                    continue

                # Format for LLM
                formatted_standings = self.format_standings_for_llm(standings)
                formatted_matches = [
                    self.format_match_for_llm(match) for match in matches
                ]

                summary = {
                    "competition": competition,
                    "standings": formatted_standings,
                    "matches": formatted_matches,
                }

                summaries.append(summary)

            except requests.RequestException as e:
                self.logger.error(f"Error fetching data for {competition}: {e}")
                continue

        return summaries

    def prep_last_day_summary(self):
        """Generate LLM-friendly summary of yesterday's match results."""
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        summaries = []

        for competition in self.competitions:
            try:
                matches = self.get_matches_for_competition(
                    competition, yesterday, yesterday
                )

                if not matches:
                    continue

                formatted_matches = [
                    self.format_match_for_llm(match) for match in matches
                ]

                summary = {"competition": competition, "matches": formatted_matches}

                summaries.append(summary)

            except requests.RequestException as e:
                self.logger.error(f"Error fetching data for {competition}: {e}")
                continue

        return summaries

    def prep_today_summary(self):
        """Generate LLM-friendly summary of today's matches."""
        today = datetime.now().date().isoformat()
        summaries = []

        for competition in self.competitions:
            try:
                matches = self.get_matches_for_competition(competition, today, today)

                if not matches:
                    continue

                formatted_matches = [
                    self.format_match_for_llm(match) for match in matches
                ]

                summary = {"competition": competition, "matches": formatted_matches}

                summaries.append(summary)

            except requests.RequestException as e:
                self.logger.error(f"Error fetching data for {competition}: {e}")
                continue

        return summaries
