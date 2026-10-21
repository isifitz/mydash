"""Settings shared across mydash. Change values here, not in the code."""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "mydash.db"
RULES_PATH = BASE_DIR / "rules.md"

TIMEZONE = "Africa/Johannesburg"
PILLARS = ["Waverley", "Music", "FixMe", "Parked"]

TITLE_MAX = 120
DONE_DEF_MIN = 3
EST_MIN, EST_MAX = 5, 600
NEXT_CAP = 3
PATH_MAX_SEGMENTS = 3

SEED_PATHS = [
    "Waverley/Products", "Waverley/Machines", "Waverley/Clients",
    "Waverley/Business-system",
    "Music/DJing", "Music/Production", "Music/Theory",
    "FixMe/Routine", "FixMe/Household", "FixMe/Work-system",
    "FixMe/Learning", "FixMe/Decentering",
    "Parked",
]

CONFIRM_STATUSES = ["now", "next", "later", "blocked", "parked"]
ALL_STATUSES = ["inbox", "now", "next", "later", "blocked", "done", "parked"]
OUTCOMES = ["done", "progress", "small_problem", "big_problem"]

MODEL = "claude-haiku-5-5"
AI_TIMEOUT_SECONDS = 10

GOOGLE_CREDENTIALS_PATH = BASE_DIR / "data" / "google_client_secret.json"
GOOGLE_TOKEN_PATH = BASE_DIR / "data" / "google_token.json"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CALENDAR_ID = "primary"
DEFAULT_EVENT_MINUTES = 60  # fallback length for a timed event with no est_minutes
