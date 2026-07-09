"""Shared configuration and paths for the pipeline."""
import os
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Windows consoles often default to cp1252, which crashes on emoji GPT-5 nano
# may include in captions. Force UTF-8 so prints never blow up mid-pipeline.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

with open(PROJECT_ROOT / "config" / "feeds.yaml", "r", encoding="utf-8") as f:
    _FEEDS_CONFIG = yaml.safe_load(f)

FEEDS = _FEEDS_CONFIG["feeds"]
SETTINGS = _FEEDS_CONFIG["settings"]

DATA_DIR = PROJECT_ROOT / "data"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5-nano"

LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8765/callback")
LINKEDIN_TOKEN_FILE = DATA_DIR / "linkedin_token.json"
LINKEDIN_API_VERSION = "202506"  # LinkedIn-Version header; bump periodically, see README.


def today_dir(day: date | None = None) -> Path:
    day = day or date.today()
    d = DATA_DIR / day.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    (d / "infographics").mkdir(exist_ok=True)
    return d
