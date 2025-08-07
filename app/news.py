import feedparser
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser
from collections import defaultdict
from datetime import timedelta
from app.logger import setup_logger
import random

# ---------- CONFIG ----------
MAX_ARTICLES = 10
KEYWORDS = [
    # EU Politics
    "european union",
    "eu",
    "brussels",
    "ec",
    "european commission",
    "european parliament",
    "european council",
    "european court",
    "european central bank",
    "european elections",
    "eu foreign policy",
    "eu diplomacy",
    "eu sanctions",
    # US Politics
    "united states",
    "us",
    "washington",
    "congress",
    "senate",
    "house of representatives",
    "white house",
    "president",
    "joe biden",
    "kamala harris",
    "us foreign policy",
    "us sanctions",
    "pentagon",
    "democrats",
    "republicans",
    "supreme court",
    # Middle East Politics
    "middle east",
    "iran",
    "iraq",
    "syria",
    "saudi arabia",
    "israel",
    "palestine",
    "uae",
    "qatar",
    "lebanon",
    "turkey",
    "yemen",
    "gcc",
    "arab league",
    "arab spring",
    "middle east peace",
    "gaza",
    "hezbollah",
    "houthi",
    "bashar al-assad",
    # Ukraine War
    "ukraine",
    "russia",
    "putin",
    "zelensky",
    "donbas",
    "crimea",
    "eastern ukraine",
    "kyiv",
    "war in ukraine",
    "ukraine conflict",
    "nato",
    "russian invasion",
    "russian military",
    "ukrainian army",
    "refugees",
    "sanctions on russia",
    # Economy
    "economy",
    "inflation",
    "gdp",
    "stock market",
    "federal reserve",
    "interest rates",
    "central bank",
    "trade",
    "recession",
    "unemployment",
    "labor market",
    "fiscal policy",
    "monetary policy",
    "budget deficit",
    "public debt",
    "economic growth",
    "financial markets",
    "cryptocurrency",
    "bitcoin",
    "blockchain",
    "economic sanctions",
    "investment",
    # Technology
    "technology",
    "tech",
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "big data",
    "blockchain",
    "5g",
    "internet of things",
    "iot",
    "cybersecurity",
    "quantum computing",
    "cloud computing",
    "software",
    "hardware",
    "semiconductors",
    "gadgets",
    "startups",
    "digital transformation",
    "automation",
    # Green Energy
    "green energy",
    "renewable energy",
    "solar power",
    "wind power",
    "hydropower",
    "electric vehicles",
    "ev",
    "battery technology",
    "energy storage",
    "carbon emissions",
    "climate change",
    "sustainability",
    "clean energy",
    "carbon neutrality",
    "net zero",
    "environmental policy",
    "green tech",
    "biofuels",
    "hydrogen energy",
    "energy transition",
    # General Political Terms
    "diplomacy",
    "sanctions",
    "geopolitics",
    "international relations",
    "foreign policy",
    "summit",
    "treaty",
    "negotiations",
    "alliance",
    "conflict",
    "peace talks",
    "strategy"
    # EU Politics (German terms)
    "europäische union",
    "eu",
    "brüssel",
    "eu-kommission",
    "eu-parlament",
    "eu-rat",
    "eu-gerichtshof",
    "europäische zentralbank",
    "eu-wahlen",
    "eu-außenpolitik",
    "sanktionen",
    # German / EU Politics in German
    "bundestag",
    "bundesregierung",
    "kanzler",
    "angela merkel",
    "olaf scholz",
    "innenpolitik",
    "außenpolitik",
    "deutsche politik",
    "deutsche wirtschaft",
    "spd",
    "cdu",
    "csu",
    "fdp",
    "grüne",
    "afd",
    # US Politics (common German references)
    "usa",
    "vereinigte staaten",
    "weißes haus",
    "präsident",
    "joe biden",
    "kamala harris",
    "kongress",
    "senat",
    "abgeordnetenhaus",
    # Middle East Politics (German terms)
    "naher osten",
    "iran",
    "irak",
    "syrien",
    "saudi-arabien",
    "israel",
    "palästina",
    "vereinigte arabische emirate",
    "katar",
    "libanon",
    "türkei",
    "jemen",
    "gcc",
    "arabische liga",
    "arabischer frühling",
    "gaza",
    "hezbollah",
    "huthi",
    "bashar al-assad",
    # Ukraine War (German terms)
    "ukraine",
    "russland",
    "putin",
    "selenskij",
    "donbass",
    "krim",
    "ostukraine",
    "kyjiw",
    "krieg in der ukraine",
    "ukraine-konflikt",
    "nato",
    "russische invasion",
    "russische armee",
    "ukrainische armee",
    "flüchtlinge",
    "sanktionen gegen russland",
    # Economy (German terms)
    "wirtschaft",
    "inflation",
    "bruttoinlandsprodukt",
    "aktienmarkt",
    "fed",
    "zinssätze",
    "zentralbank",
    "handel",
    "rezession",
    "arbeitslosigkeit",
    "arbeitsmarkt",
    "finanzpolitik",
    "geldpolitik",
    "haushaltsdefizit",
    "staatsverschuldung",
    "wirtschaftswachstum",
    "finanzmärkte",
    "kryptowährung",
    "bitcoin",
    "blockchain",
    "wirtschaftssanktionen",
    "investitionen",
    # Technology (German terms)
    "technologie",
    "technik",
    "ki",
    "künstliche intelligenz",
    "maschinelles lernen",
    "deep learning",
    "big data",
    "blockchain",
    "5g",
    "internet der dinge",
    "iot",
    "cybersicherheit",
    "quantencomputing",
    "cloud computing",
    "software",
    "hardware",
    "halbleiter",
    "geräte",
    "startups",
    "digitale transformation",
    "automatisierung",
    # Green Energy (German terms)
    "erneuerbare energie",
    "grüne energie",
    "solarenergie",
    "windenergie",
    "wasserkraft",
    "elektrofahrzeuge",
    "ev",
    "batterietechnologie",
    "energiespeicherung",
    "kohlenstoffemissionen",
    "klimawandel",
    "nachhaltigkeit",
    "saubere energie",
    "klimaneutralität",
    "netto null",
    "umweltpolitik",
    "grüne technologie",
    "biokraftstoffe",
    "wasserstoffenergie",
    "energiewende",
    # General Political Terms (German)
    "diplomatie",
    "sanktionen",
    "geopolitik",
    "internationale beziehungen",
    "außenpolitik",
    "gipfel",
    "vertrag",
    "verhandlungen",
    "allianz",
    "konflikt",
    "friedensgespräche",
    "strategie",
]
# ----------------------------


class NewsAggregatorTool:
    def __init__(self, file):
        self.logger = setup_logger(__name__)
        urls = self.load_rss_urls(file)
        self.entries = self.fetch_entries(urls)

    def load_rss_urls(self, file_path):
        """Load RSS URLs from a file, one per line."""
        return [
            line.strip()
            for line in Path(file_path).read_text().splitlines()
            if line.strip()
        ]

    def fetch_entries(self, urls):
        """Fetch all articles from the list of feeds."""
        all_entries = []
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = entry.get("published", "") or entry.get("updated", "")
                try:
                    dt = date_parser.parse(published) if published else datetime.min
                    dt_naive = dt.replace(tzinfo=None)
                except Exception:
                    dt_naive = datetime.min  # fallback if parsing fails
                all_entries.append(
                    {
                        "title": entry.get("title", "No title"),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "published": published,
                        "published_parsed": dt_naive,
                    }
                )
        return all_entries

    def summarize_prep(self) -> str:
        """Prepare a text block for LLM summarization."""
        sorted_entries = sorted(
            self.entries, key=lambda e: e["published_parsed"], reverse=True
        )
        blocks = [
            f"📰 Title: {e['title']}\n📌 Link: {e['link']}\n📝 Summary: {e['summary']}\n"
            for e in sorted_entries
        ]
        return "\n\n".join(blocks)

    def limit_per_source(self, max_per_source=4):
        source_map = defaultdict(list)
        for entry in self.entries:
            source = entry["link"].split("/")[2]  # domain name as source
            source_map[source].append(entry)

        reduced = []
        for source, source_entries in source_map.items():
            sorted_entries = sorted(
                source_entries,
                key=lambda e: (e.get("score", 0), e.get("published_parsed")),
                reverse=True,
            )
            reduced.extend(sorted_entries[:max_per_source])

        self.entries = reduced
        return self

    def filter_recent(self, hours=48):
        cutoff = datetime.now() - timedelta(hours=hours)
        self.entries = [e for e in self.entries if e["published_parsed"] > cutoff]
        return self

    def filter_summary(self):
        entries = [e for e in self.entries if e["summary"].strip()]
        self.entries = entries
        return self

    def filter_duplicates(self):
        seen = set()
        unique_entries = []
        for e in self.entries:
            title_lower = e["title"].strip().lower()
            if title_lower not in seen:
                seen.add(title_lower)
                unique_entries.append(e)
        self.entries = unique_entries
        return self

    def shuffle_and_slice(self, total_limit=MAX_ARTICLES):
        while len(self.entries) < total_limit:
            total_limit -= 3

        random.shuffle(self.entries)
        self.entries = self.entries[:total_limit]
        return self

    def weighted_selection(self, total_limit=MAX_ARTICLES * 2):
        while total_limit >= len(self.entries):
            total_limit = len(self.entries) - 3

        now = datetime.now()
        weighted_entries = []

        for e in self.entries:
            # Time decay: newer articles are preferred
            age_hours = (now - e["published_parsed"]).total_seconds() / 3600
            freshness = max(0.1, 1 / (1 + age_hours))

            # Combine freshness and keyword score
            weight = freshness * (1 + e.get("score", 0))
            weighted_entries.append((e, weight))

        # Normalize and sample
        total_weight = sum(w for _, w in weighted_entries)
        probabilities = [w / total_weight for _, w in weighted_entries]
        selected = random.choices(
            [e for e, _ in weighted_entries],
            weights=probabilities,
            k=min(total_limit * 2, len(weighted_entries)),
        )
        self.entries = selected
        return self

    def score_by_keywords(self, keywords=KEYWORDS):
        keywords = [k.lower() for k in keywords]
        for entry in self.entries:
            text = (entry["title"] + " " + entry["summary"]).lower()
            score = sum(text.count(k.lower()) for k in keywords)
            entry["score"] = score
        return self
